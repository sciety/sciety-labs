SELECT
  event_timestamp,
  event_name,
  sciety_list,
  sciety_user,
  article_id
FROM `elife-data-pipeline.de_proto.v_sciety_event` AS event
WHERE
  event_name IN ('ArticleAddedToList', 'ArticleRemovedFromList')
  AND sciety_list.list_id IN (
    '454ba80f-e0bc-47ed-ba76-c8f872c303d2',
    'dcc7c864-6630-40e7-8eeb-9fb6f012e92b',
    'bea18573-30a9-43e7-b2e5-fb08d7ba2419'
  )
ORDER BY event_timestamp
