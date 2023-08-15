class ScietyEventNames:
    ARTICLE_ADDED_TO_LIST = 'ArticleAddedToList'
    ARTICLE_REMOVED_FROM_LIST = 'ArticleRemovedFromList'
    ANNOTATION_CREATED = 'AnnotationCreated'
    EVALUATION_RECORDED = 'EvaluationRecorded'
    EVALUATION_PUBLICATION_RECORDED = 'EvaluationPublicationRecorded'


ALTERNATIVE_EVALUATION_RECORDED_EVENT_NAMES = {
    ScietyEventNames.EVALUATION_RECORDED,
    ScietyEventNames.EVALUATION_PUBLICATION_RECORDED
}
