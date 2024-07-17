SELECT
  event.event_timestamp,
  event.normalized_event_name AS event_name,
  event.sciety_list,
  event.sciety_user,
  event.sciety_group,
  event.article_id,
  event.evaluation_locator,
  event.published_at_timestamp,
  event.content
FROM `elife-data-pipeline.prod.v_sciety_event` AS event
WHERE NOT event.is_duplicate_event
ORDER BY event_timestamp
