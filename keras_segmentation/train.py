import argparse
import json
from .data_utils.data_loader import image_segmentation_generator , verify_segmentation_dataset
from .models import model_from_name
import os
import six
import tensorflow as tf
import keras

# define iou or jaccard loss function
def iou_loss(y_true, y_pred):
    y_true_rs = tf.reshape(y_true, [-1])
    y_pred_rs = tf.reshape(y_pred, [-1])

    intersection = tf.reduce_sum(y_true_rs * y_pred_rs)
    score = (intersection + 1.) / (tf.reduce_sum(y_true_rs) + tf.reduce_sum(y_pred_rs) - intersection + 1.)
    return 1 - score

# combine bce loss and iou loss
def iou_bce_loss(y_true, y_pred):
    return 0.5 * keras.losses.binary_crossentropy(y_true, y_pred) + 0.5 * iou_loss(y_true, y_pred)

def mean_iou(y_true, y_pred):
    y_pred = tf.round(y_pred)
    intersect = tf.reduce_sum(y_true * y_pred, axis=[1, 2, 3])
    union = tf.reduce_sum(y_true, axis=[1, 2, 3]) + tf.reduce_sum(y_pred, axis=[1, 2, 3])
    smooth = tf.ones(tf.shape(intersect))
    return tf.reduce_mean((intersect + smooth) / (union - intersect + smooth))


def find_latest_checkpoint( checkpoints_path ):
	ep = 0
	r = None
	while True:
		if os.path.isfile( checkpoints_path + "." + str( ep )  ):
			r = checkpoints_path + "." + str( ep ) 
		else:
			return r 

		ep += 1




def train( model  , 
		train_images  , 
		train_annotations , 
		input_height=None , 
		input_width=None , 
		n_classes=None,
		verify_dataset=True,
		checkpoints_path=None , 
		epochs = 5,
		batch_size = 2,
		validate=False , 
		val_images=None , 
		val_annotations=None ,
		val_batch_size=2 , 
		auto_resume_checkpoint=False ,
		load_weights=None ,
		steps_per_epoch=512,
		optimizer_name='adadelta',
		lossfn='categorical_crossentropy',
		use_multiprocessing=True
	):


	if  isinstance(model, six.string_types) : # check if user gives model name insteead of the model object
		# create the model from the name
		assert ( not n_classes is None ) , "Please provide the n_classes"
		if (not input_height is None ) and ( not input_width is None):
			model = model_from_name[ model ](  n_classes , input_height=input_height , input_width=input_width )
		else:
			model = model_from_name[ model ](  n_classes )

	n_classes = model.n_classes
	input_height = model.input_height
	input_width = model.input_width
	output_height = model.output_height
	output_width = model.output_width


	if validate:
		assert not (  val_images is None ) 
		assert not (  val_annotations is None ) 

	if not optimizer_name is None:
		if lossfn == 'iou_loss':
			lossfn = iou_loss
		elif lossfn == 'iou_bce_loss':
			lossfn == iou_bce_loss

		model.compile(loss=lossfn,
			optimizer= optimizer_name ,
			metrics=['accuracy'])

	if not checkpoints_path is None:
		open( checkpoints_path+"_config.json" , "w" ).write( json.dumps( {
			"model_class" : model.model_name ,
			"n_classes" : n_classes ,
			"input_height" : input_height ,
			"input_width" : input_width ,
			"output_height" : output_height ,
			"output_width" : output_width 
		}))

	if ( not (load_weights is None )) and  len( load_weights ) > 0:
		print("Loading weights from " , load_weights )
		model.load_weights(load_weights)

	if auto_resume_checkpoint and ( not checkpoints_path is None ):
		latest_checkpoint = find_latest_checkpoint( checkpoints_path )
		if not latest_checkpoint is None:
			print("Loading the weights from latest checkpoint "  ,latest_checkpoint )
			model.load_weights( latest_checkpoint )


	if verify_dataset:
		print("Verifying train dataset")
		verify_segmentation_dataset( train_images , train_annotations , n_classes )
		if validate:
			print("Verifying val dataset")
			verify_segmentation_dataset( val_images , val_annotations , n_classes )


	train_gen = image_segmentation_generator( train_images , train_annotations ,  batch_size,  n_classes , input_height , input_width , output_height , output_width   )


	if validate:
		val_gen  = image_segmentation_generator( val_images , val_annotations ,  val_batch_size,  n_classes , input_height , input_width , output_height , output_width   )


	if not validate:
		for ep in range( epochs ):
			print("Starting Epoch " , ep )
			model.fit_generator( train_gen , steps_per_epoch  , epochs=1, use_multiprocessing=use_multiprocessing )
			if not checkpoints_path is None:
				model.save_weights( checkpoints_path + "." + str( ep ) )
				print("saved " , checkpoints_path + ".model." + str( ep ) )
			print("Finished Epoch" , ep )
	else:
		for ep in range( epochs ):
			print("Starting Epoch " , ep )
			model.fit_generator( train_gen , steps_per_epoch  , validation_data=val_gen , validation_steps=200 ,  epochs=1, use_multiprocessing=use_multiprocessing )
			if not checkpoints_path is None:
				model.save_weights( checkpoints_path + "." + str( ep )  )
				print("saved " , checkpoints_path + ".model." + str( ep ) )
			print("Finished Epoch" , ep )





