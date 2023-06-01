SELECT
  event.event_timestamp,
  event.normalized_event_name AS event_name,
  event.sciety_list,
  event.sciety_user,
  event.sciety_group,
  event.article_id,
  event.evaluation_locator,
  event.content
FROM `elife-data-pipeline.de_proto.v_sciety_event` AS event
WHERE
  (
    event.normalized_event_name IN ('ArticleAddedToList', 'ArticleRemovedFromList', 'AnnotationCreated')
    AND event.sciety_list.list_id NOT IN (
      -- exclude some lists of users who's avatar no longer resolves
      'c145fb46-9487-4910-ae25-aa3e9f3fa5e8',
      'b8b1abc5-9b8e-42b7-bc10-e01572d1d5d4',
      '8f612ad9-fb88-461a-ab38-4b7f681e8ffe',
      '36c8bff1-f5f2-4c8a-b2b2-190af01ad9e6',
      'e89549c2-6dc6-4d31-a72f-e6b90a496458',
      '7223b4bf-2163-4f45-9457-7bd9524cf779',
      'a9bf8053-032d-421e-ab5c-4a9cb88b91b4',
      '78fc6d8c-8bca-49e8-86cc-8a676688d476',
      'c8ccd202-b62f-4c92-897c-3c1fb6275401',
      '55b5810b-d255-46d1-8372-7cf4f16595b9',
      '0e634779-68fa-4209-87f7-8cb5046a3c94'
    )
    AND NOT event.is_duplicate_event
  ) OR (
    event.normalized_event_name IN (
        'EvaluationRecorded',
        'IncorrectlyRecordedEvaluationErased'
    )
  )
ORDER BY event_timestamp
