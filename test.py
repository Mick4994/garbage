from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
garbage_classification = pipeline(Tasks.image_classification,
                                    model='damo/cv_convnext-base_image-classification_garbage')
print(garbage_classification('./fruit.jpg'))