import dataclasses
from datetime import date, datetime
import re
from typing import AsyncIterable, Iterable, Mapping, NamedTuple, Optional, Sequence, TypeVar

from sciety_labs.models.image import ObjectImages


DOI_ARTICLE_ID_PREFIX = 'doi:'


# Potential Preprint servers:
# - 10.1101: bioRxiv, medRxiv (Cold Spring Harbor Laboratory in general)
# - 10.21203: Research Square (https://www.researchsquare.com/)
# - 10.20944: Preprints.org
# - 10.31234: PsyArXiv (https://psyarxiv.com/), part of OSF Preprints
# - 10.22541: Authorea Preprints (https://www.authorea.com)
# - 10.2139: SSRN (https://papers.ssrn.com)
# - 10.12688: F1000 (https://f1000research.com/, also https://wellcomeopenresearch.org)
#             F1000 itself says not preprints because they can't be published to a journal.
# - 10.26434: ChemRxiv (https://chemrxiv.org)
# - 10.7287: PeerJ (https://peerj.com/)
# - 10.1590: SciELO Preprints (https://preprints.scielo.org/);
#            DOI prefix may also contain non-preprints


class KnownDoiPrefix:
    BIORXIV_MEDRXIV = '10.1101'
    RESEARCH_SQUARE = '10.21203'
    PREPRINTS_ORG = '10.20944'
    PSYARXIV = '10.31234'
    AUTHOREA_PREPRINTS = '10.22541'
    SSRN = '10.2139'
    F1000 = '10.12688'
    CHEMRXIV = '10.26434'
    PEERJ = '10.7287'
    SCIELO = '10.1590'


_ALL_PREPRINT_DOI_PREFIX_SET = {
    KnownDoiPrefix.BIORXIV_MEDRXIV,
    KnownDoiPrefix.RESEARCH_SQUARE,
    KnownDoiPrefix.PREPRINTS_ORG,
    KnownDoiPrefix.PSYARXIV,
    KnownDoiPrefix.AUTHOREA_PREPRINTS,
    KnownDoiPrefix.SSRN,
    KnownDoiPrefix.CHEMRXIV,
    KnownDoiPrefix.PEERJ
}


_DOI_PREFIX_NOT_SUPPORTED_BY_SCIETY_SET = {
    KnownDoiPrefix.PREPRINTS_ORG,
    KnownDoiPrefix.AUTHOREA_PREPRINTS,
    KnownDoiPrefix.SSRN,
    KnownDoiPrefix.CHEMRXIV
}


_PREPRINT_DOI_PREFIX_SET = _ALL_PREPRINT_DOI_PREFIX_SET - _DOI_PREFIX_NOT_SUPPORTED_BY_SCIETY_SET


_KNOWN_PREPRINT_SERVER_REGEXP_SET = {
    r'10\.1590/SciELOPreprints.*',
    r'[^/]+/osf\.io/.*'
}


def is_doi_article_id(article_id: str) -> bool:
    return article_id.startswith(DOI_ARTICLE_ID_PREFIX)


def get_doi_from_article_id_or_none(article_id: str) -> Optional[str]:
    if not is_doi_article_id(article_id):
        return None
    return article_id[len(DOI_ARTICLE_ID_PREFIX):]


def _get_doi_prefix(article_doi: str) -> str:
    doi_prefix, _ = article_doi.split('/', maxsplit=1)
    return doi_prefix


def is_preprint_doi(article_doi: str) -> bool:
    doi_prefix = _get_doi_prefix(article_doi)
    if doi_prefix in _PREPRINT_DOI_PREFIX_SET:
        return True
    for preprint_server_regexp in _KNOWN_PREPRINT_SERVER_REGEXP_SET:
        if re.match(preprint_server_regexp, article_doi, re.RegexFlag.IGNORECASE):
            return True
    return False


class ArticleMetaData(NamedTuple):
    article_doi: str
    article_title: str
    abstract: Optional[str] = None
    author_name_list: Optional[Sequence[str]] = None
    published_date: Optional[date] = None


class ArticleStats(NamedTuple):
    evaluation_count: int = 0


class ArticleAuthor(NamedTuple):
    name: str


class ArticleComment(NamedTuple):
    text: str
    author: ArticleAuthor


@dataclasses.dataclass(frozen=True)
class ArticleMention:
    article_doi: str
    created_at_timestamp: Optional[datetime] = None
    comment: Optional[ArticleComment] = None
    external_reference_by_name: Mapping[str, str] = dataclasses.field(default_factory=dict)
    article_meta: Optional[ArticleMetaData] = None
    article_stats: Optional[ArticleStats] = None
    article_images: Optional[ObjectImages] = None

    def _replace(self, **changes) -> 'ArticleMention':
        return dataclasses.replace(self, **changes)

    def get_created_at_sort_key(self) -> datetime:
        assert self.created_at_timestamp
        return self.created_at_timestamp

    def get_published_date_sort_key(self) -> date:
        assert self.article_meta
        assert self.article_meta.published_date
        return self.article_meta.published_date

    @staticmethod
    def get_sorted_by_publication_date(
        iterable: Iterable['ArticleMention']
    ) -> Sequence['ArticleMention']:
        return sorted(iterable, key=ArticleMention.get_published_date_sort_key, reverse=True)


ArticleMentionT = TypeVar('ArticleMentionT', bound=ArticleMention)


@dataclasses.dataclass(frozen=True)
class ArticleSearchResultItem(ArticleMention):
    pass


def iter_preprint_article_mention(
    article_mention_iterable: Iterable[ArticleMentionT]
) -> Iterable[ArticleMentionT]:
    return (
        article_mention
        for article_mention in article_mention_iterable
        if is_preprint_doi(article_mention.article_doi)
    )


async def async_iter_preprint_article_mention(
    article_mention_iterable: AsyncIterable[ArticleMentionT]
) -> AsyncIterable[ArticleMentionT]:
    async for article_mention in article_mention_iterable:
        if is_preprint_doi(article_mention.article_doi):
            yield article_mention
