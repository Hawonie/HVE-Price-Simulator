from dataclasses import dataclass, field


@dataclass
class FieldSelectors:
    """Ordered list of CSS selectors for a single field. First match wins."""
    selectors: list[str]


# Per-field fallback selector chains
SELECTOR_CONFIG: dict[str, FieldSelectors] = {
    "title": FieldSelectors(selectors=[
        "#productTitle",
        "#title span",
        "h1.product-title-word-break span",
    ]),
    "current_price": FieldSelectors(selectors=[
        "#corePriceDisplay_desktop_feature_div .a-offscreen",
        "#corePrice_desktop .a-offscreen",
        "span.priceToPay .a-offscreen",
        "#corePrice_feature_div .a-offscreen",
        "#apex_desktop .a-price .a-offscreen",
        ".reinventPricePriceToPayMargin .a-offscreen",
        "#tp_price_block_total_price_ww .a-offscreen",
        "#price_inside_buybox",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#newBuyBoxPrice",
    ]),
    "list_price": FieldSelectors(selectors=[
        "span.a-price.a-text-price .a-offscreen",
        "#priceblock_listprice",
        "span.priceBlockStrikePriceString",
    ]),
    "rating": FieldSelectors(selectors=[
        "#acrPopover span.a-icon-alt",
        "span[data-hook='rating-out-of-text']",
        "#averageCustomerReviews span.a-icon-alt",
    ]),
    "review_count": FieldSelectors(selectors=[
        "#acrCustomerReviewText",
        "span[data-hook='total-review-count']",
        "#acrCustomerReviewLink span",
    ]),
    "main_image_url": FieldSelectors(selectors=[
        "#landingImage",
        "#imgBlkFront",
        "#main-image",
    ]),
    "brand": FieldSelectors(selectors=[
        "#bylineInfo",
        "#brand",
        ".po-brand .a-span9 span",
    ]),
    "seller_info": FieldSelectors(selectors=[
        "#sellerProfileTriggerId",
        "#merchant-info",
        "#tabular-buybox .tabular-buybox-text span",
    ]),
}
