from typing import Iterable, Optional

from sciety_labs.models.article import ArticleImages, ArticleMention


class GoogleSheetArticleImageProvider:
    def get_article_image_url_by_doi(self, article_doi: str) -> Optional[str]:
        if article_doi == '10.1101/2023.01.12.523782':
            return (
                'https://storage.googleapis.com/public-article-images/generated/'
                '20230315235915-Cell%20lines%2C%20photography%2C%20canon%2C%20'
                'blurred%20background-1.jpg'
            )
        return None

    def get_article_images_by_doi(self, article_doi: str) -> ArticleImages:
        return ArticleImages(
            image_url=self.get_article_image_url_by_doi(article_doi)
        )

    def iter_article_mention_with_article_image_url(
        self,
        article_mention_iterable: Iterable[ArticleMention]
    ) -> Iterable[ArticleMention]:
        return (
            article_mention._replace(
                article_images=self.get_article_images_by_doi(
                    article_mention.article_doi
                )
            )
            for article_mention in article_mention_iterable
        )
