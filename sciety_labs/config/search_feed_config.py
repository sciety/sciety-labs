from typing import Mapping, NamedTuple, Optional

import yaml


class SearchFeedConfig(NamedTuple):
    title: str
    description: str
    image_url: str
    query: str
    wide_image_url: Optional[str] = None


class SearchFeedsConfig(NamedTuple):
    feeds_by_slug: Mapping[str, SearchFeedConfig]


def load_search_feeds_config(
    config_file: str
) -> SearchFeedsConfig:
    with open(config_file, 'r', encoding='utf-8') as config_fp:
        config_dict = yaml.load(config_fp, yaml.SafeLoader)
    return SearchFeedsConfig(
        feeds_by_slug={
            feed_dict['slug']: SearchFeedConfig(
                title=feed_dict['title'],
                description=feed_dict['description'],
                image_url=feed_dict['image_url'],
                wide_image_url=feed_dict.get('wide_image_url'),
                query=feed_dict['query']
            )
            for feed_dict in config_dict['feeds']
        }
    )
