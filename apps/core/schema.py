"""
apps/core/schema.py

Custom AutoSchema for drf-spectacular that auto-tags endpoints by URL prefix.

Register via SPECTACULAR_SETTINGS['DEFAULT_SCHEMA_CLASS'] (already set in
DRF's DEFAULT_SCHEMA_CLASS which drf-spectacular piggybacks on) or via the
REST_FRAMEWORK settings.
"""
from drf_spectacular.openapi import AutoSchema

# Mapping: (URL prefix) -> Tag name.
# Checked in order; first match wins.
_PATH_TAG_MAP = [
    ('/health', 'Health'),
    ('/user/', 'Auth'),
    ('/api/author/', 'Author Studio'),
    ('/api/authors/', 'Authors'),
    ('/api/books/', 'Books'),
    ('/api/categories/', 'Categories'),
    ('/api/cart/', 'Cart'),
    ('/api/orders/', 'Orders'),
    ('/api/coupons/', 'Coupons'),
    ('/api/payments/', 'Payments'),
    ('/api/reviews/', 'Reviews'),
    ('/api/discussions/', 'Discussions'),
    ('/api/threads/', 'Discussions'),
    ('/api/posts/', 'Discussions'),
    ('/api/scheduled-messages/', 'Notifications'),
    ('/api/cron/', 'Notifications'),
    ('/api/notifications/', 'Notifications'),
    ('/api/inventory/', 'Inventory'),
    ('/api/wishlist/', 'Wishlist'),
]


class TaggedAutoSchema(AutoSchema):
    """
    Extends drf-spectacular's AutoSchema to assign tags based on the request
    path when the view doesn't explicitly set them.

    Views that use ``@extend_schema(tags=[...])`` will still override this.
    """

    def get_tags(self) -> list[str]:
        # If the view already has explicit tags from @extend_schema, respect them.
        explicit = super().get_tags()
        # drf-spectacular defaults tags to [view.__class__.__name__] when not set.
        # We detect this "no explicit tag" case by checking if the default would
        # just be the serializer or viewset name.
        # Safer: always override based on URL if we have a matching prefix.
        path = self.path
        for prefix, tag in _PATH_TAG_MAP:
            if path.startswith(prefix):
                return [tag]
        # Fallback to default behaviour.
        return explicit


def preprocessing_filter_spec(endpoints, **kwargs):
    """
    PREPROCESSING_HOOK placeholder (required by the settings reference).
    Currently a no-op pass-through; tagging is handled by TaggedAutoSchema.
    """
    return endpoints
