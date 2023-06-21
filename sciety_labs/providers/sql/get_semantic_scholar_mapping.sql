SELECT
  response.paperId AS paper_id,
  response.externalIds.DOI AS article_doi
FROM `elife-data-pipeline.de_proto.v_semantic_scholar_response` AS response
