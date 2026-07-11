import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal


DEFAULTS = {
    "products": 72,
    "warehouses": 6,
    "sales": 12000,
    "days": 180,
    "return_rate": 0.045,
    "seed": 42,
}

REGIONS = ["DE-BY", "DE-BE", "DE-NW", "DE-HE", "DE-HH", "DE-BW", "DE-SN"]
CHANNELS = ["online", "retail", "b2b", "marketplace"]
COMPETITORS = ["Amazin", "ShopHub", "ElectroBay", "DealNest", "MarketSquare"]
COLORS = ["Midnight", "Silver", "Graphite", "Blue", "Forest", "White", "Rose"]

CATEGORY_BLUEPRINTS = [
    {
        "name": "Laptops",
        "slug": "electronics-laptops",
        "parent": "Electronics",
        "brands": ["NovaBook", "ZenCore", "Astra", "OmniPeak"],
        "models": ["Pro", "Air", "Studio", "Edge"],
        "use_cases": ["remote work", "student productivity", "video editing", "software development"],
        "audience": "students, creators, analysts, and hybrid professionals",
    },
    {
        "name": "Smartphones",
        "slug": "electronics-smartphones",
        "parent": "Electronics",
        "brands": ["Astra", "BrightCo", "NovaWorks", "ZenCore"],
        "models": ["One", "PixelMax", "Ultra", "Mini"],
        "use_cases": ["mobile photography", "travel", "business communication", "gaming"],
        "audience": "mobile-first customers, creators, and frequent travelers",
    },
    {
        "name": "Headphones",
        "slug": "electronics-headphones",
        "parent": "Electronics",
        "brands": ["NordicLine", "Astra", "OmniPeak", "BrightCo"],
        "models": ["Quiet", "Pulse", "Studio", "Run"],
        "use_cases": ["commuting", "work calls", "fitness", "music production"],
        "audience": "commuters, athletes, remote workers, and audio enthusiasts",
    },
    {
        "name": "Coffee Machines",
        "slug": "home-coffee-machines",
        "parent": "Home & Kitchen",
        "brands": ["Kraftly", "NordicLine", "BrightCo", "NovaWorks"],
        "models": ["Brew", "Barista", "Crema", "Compact"],
        "use_cases": ["home espresso", "small office", "milk drinks", "quick morning coffee"],
        "audience": "home baristas, small offices, and coffee lovers",
    },
    {
        "name": "Running Shoes",
        "slug": "sports-running-shoes",
        "parent": "Sports",
        "brands": ["OmniPeak", "NordicLine", "Astra", "BrightCo"],
        "models": ["Stride", "Trail", "Tempo", "Cloud"],
        "use_cases": ["daily training", "wet roads", "trail running", "long-distance running"],
        "audience": "new runners, marathon trainees, and outdoor athletes",
    },
    {
        "name": "Office Chairs",
        "slug": "office-chairs",
        "parent": "Office",
        "brands": ["ZenCore", "NordicLine", "Kraftly", "OmniPeak"],
        "models": ["Ergo", "Flex", "Mesh", "Executive"],
        "use_cases": ["home office", "long desk sessions", "gaming setup", "shared office"],
        "audience": "remote workers, office managers, gamers, and students",
    },
    {
        "name": "Air Conditioners",
        "slug": "home-air-conditioners",
        "parent": "Home & Kitchen",
        "brands": ["NordicLine", "BrightCo", "ZenCore", "Astra"],
        "models": ["Cool", "Breeze", "Climate", "Portable"],
        "use_cases": ["summer heatwaves", "bedroom cooling", "home office comfort", "humid weather"],
        "audience": "families, renters, remote workers, and customers in hot regions",
    },
    {
        "name": "Space Heaters",
        "slug": "home-space-heaters",
        "parent": "Home & Kitchen",
        "brands": ["Kraftly", "NordicLine", "OmniPeak", "BrightCo"],
        "models": ["Warm", "Ceramic", "EcoHeat", "Compact"],
        "use_cases": ["winter cold snaps", "small room heating", "home office warmth", "energy-saving spot heating"],
        "audience": "apartment residents, office workers, students, and winter shoppers",
    },
    {
        "name": "Rain Jackets",
        "slug": "sports-rain-jackets",
        "parent": "Sports",
        "brands": ["OmniPeak", "NordicLine", "Astra", "NovaWorks"],
        "models": ["Storm", "TrailShell", "Commuter", "Packable"],
        "use_cases": ["rainy commutes", "hiking", "wind protection", "spring and autumn travel"],
        "audience": "commuters, hikers, cyclists, and travelers in rainy regions",
    },
    {
        "name": "Sunscreen",
        "slug": "beauty-sunscreen",
        "parent": "Beauty",
        "brands": ["BrightCo", "Astra", "NordicLine", "Kraftly"],
        "models": ["Daily SPF", "Sport SPF", "Sensitive", "Kids"],
        "use_cases": ["summer holidays", "outdoor sports", "daily UV protection", "beach travel"],
        "audience": "families, athletes, travelers, and skincare-focused customers",
    },
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace(" ", "-")
        .replace("--", "-")
    )


def money(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def ensure_clean_start(db: Session) -> None:
    tables = [
        "market_signals",
        "competitor_prices",
        "product_reviews",
        "product_specs",
        "product_images",
        "returns",
        "sales",
        "inventory",
        "product_variants",
        "products",
        "categories",
        "warehouses",
    ]
    db.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"))
    db.commit()


def seed_categories(db: Session) -> dict[str, models.Category]:
    now = utcnow()
    parents: dict[str, models.Category] = {}
    for parent in sorted({blueprint["parent"] for blueprint in CATEGORY_BLUEPRINTS}):
        category = models.Category(
            name=parent,
            slug=slugify(parent),
            description=f"Marketplace department for {parent.lower()} products.",
            created_at=now,
            updated_at=now,
        )
        db.add(category)
        parents[parent] = category
    db.commit()

    categories: dict[str, models.Category] = {}
    for blueprint in CATEGORY_BLUEPRINTS:
        category = models.Category(
            parent_category_id=parents[blueprint["parent"]].category_id,
            name=blueprint["name"],
            slug=blueprint["slug"],
            description=(
                f"{blueprint['name']} with structured specifications, variants, images, "
                "reviews, inventory, sales history, and market signals for agent analysis."
            ),
            created_at=now,
            updated_at=now,
        )
        db.add(category)
        categories[blueprint["name"]] = category
    db.commit()
    return categories


def base_price_for(category: str) -> float:
    ranges = {
        "Laptops": (699, 2499),
        "Smartphones": (349, 1399),
        "Headphones": (69, 399),
        "Coffee Machines": (89, 899),
        "Running Shoes": (59, 229),
        "Office Chairs": (119, 749),
        "Air Conditioners": (249, 1199),
        "Space Heaters": (39, 299),
        "Rain Jackets": (49, 249),
        "Sunscreen": (8, 39),
    }
    low, high = ranges[category]
    return random.uniform(low, high)


def build_descriptions(name: str, category: str, use_cases: list[str], audience: str) -> tuple[str, str]:
    short = f"{name} is built for {', '.join(use_cases[:2])} with practical features for {audience}."
    long = (
        f"{name} is a marketplace-ready {category.lower()} product designed for {audience}. "
        f"It is positioned for {', '.join(use_cases)} and includes enough structured detail for "
        "support agents to compare fit, explain compatibility, discuss warranty and return rules, "
        "and recommend alternatives based on inventory, reviews, sales velocity, and market demand."
    )
    return short, long


def seed_products(db: Session, categories: dict[str, models.Category], count: int):
    now = utcnow()
    products: list[models.Product] = []
    products_by_category: dict[str, list[models.Product]] = {name: [] for name in categories}
    per_category = max(1, count // len(CATEGORY_BLUEPRINTS))

    for blueprint in CATEGORY_BLUEPRINTS:
        for index in range(1, per_category + 1):
            brand = random.choice(blueprint["brands"])
            model = random.choice(blueprint["models"])
            name = f"{brand} {model} {blueprint['name'][:-1] if blueprint['name'].endswith('s') else blueprint['name']} {index}"
            sku = f"{blueprint['slug'].split('-')[-1].upper()}-{index:04d}"
            price = base_price_for(blueprint["name"])
            short, long = build_descriptions(name, blueprint["name"], blueprint["use_cases"], blueprint["audience"])
            product = models.Product(
                category_id=categories[blueprint["name"]].category_id,
                sku=sku,
                name=name,
                slug=f"{slugify(name)}-{index}",
                short_description=short,
                long_description=long,
                category=blueprint["name"],
                brand=brand,
                manufacturer=f"{brand} GmbH",
                model_number=f"{brand[:3].upper()}-{random.randint(1000, 9999)}",
                tags=[blueprint["name"].lower(), brand.lower(), *blueprint["use_cases"][:3]],
                use_cases=blueprint["use_cases"],
                target_audience=blueprint["audience"],
                warranty_months=random.choice([12, 18, 24, 36]),
                return_window_days=random.choice([14, 30, 45]),
                care_instructions=care_instructions_for(blueprint["name"]),
                compatibility_notes=compatibility_for(blueprint["name"]),
                included_accessories=accessories_for(blueprint["name"]),
                safety_notes=safety_notes_for(blueprint["name"]),
                currency="EUR",
                price=money(price),
                cost=money(price * random.uniform(0.48, 0.72)),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(product)
            products.append(product)
            products_by_category[blueprint["name"]].append(product)

    db.commit()
    return products, products_by_category


def care_instructions_for(category: str) -> str:
    return {
        "Laptops": "Keep vents clear, update firmware regularly, and use a padded sleeve for transport.",
        "Smartphones": "Use a protective case, avoid extreme temperatures, and clean ports with dry tools only.",
        "Headphones": "Wipe ear pads after use and store in the included case when travelling.",
        "Coffee Machines": "Descale monthly, rinse removable parts weekly, and use filtered water for best taste.",
        "Running Shoes": "Air dry after use, avoid machine drying, and rotate pairs for longer foam life.",
        "Office Chairs": "Tighten bolts quarterly and clean fabric or mesh with mild soap only.",
        "Air Conditioners": "Clean filters every two weeks during summer and keep intake vents unobstructed.",
        "Space Heaters": "Keep dust away from vents and store unplugged outside winter season.",
        "Rain Jackets": "Wash with technical outerwear detergent and reproof the water-repellent coating seasonally.",
        "Sunscreen": "Store below 30C, close cap tightly, and replace after expiry or heat exposure.",
    }[category]


def compatibility_for(category: str) -> str:
    return {
        "Laptops": "Compatible with USB-C docks, Bluetooth accessories, external monitors, and standard cloud productivity tools.",
        "Smartphones": "Compatible with Qi chargers, Bluetooth wearables, USB-C accessories, and major mobile payment systems.",
        "Headphones": "Compatible with Bluetooth phones, laptops, tablets, and USB-C charging cables.",
        "Coffee Machines": "Works with standard EU power outlets and medium-grind coffee unless capsule support is listed in specs.",
        "Running Shoes": "Best matched by gait, terrain, and weekly mileage rather than street-shoe size alone.",
        "Office Chairs": "Compatible with standard desks between 70cm and 78cm high; check seat height for shorter users.",
        "Air Conditioners": "Check room size, window hose placement, plug type, and drainage needs before buying.",
        "Space Heaters": "Use only on stable floors with standard indoor EU outlets; not intended for bathrooms unless IP-rated.",
        "Rain Jackets": "Designed to layer over base and mid layers; check size if wearing over office clothes or backpacks.",
        "Sunscreen": "Choose SPF and skin type carefully; water resistance matters for beach, sport, and humid weather.",
    }[category]


def accessories_for(category: str) -> list[str]:
    return {
        "Laptops": ["USB-C charger", "quick start guide", "recycled cardboard sleeve"],
        "Smartphones": ["USB-C cable", "SIM tool", "quick start guide"],
        "Headphones": ["carry pouch", "USB-C cable", "audio cable"],
        "Coffee Machines": ["water filter", "cleaning brush", "measuring scoop"],
        "Running Shoes": ["spare laces", "fit guide"],
        "Office Chairs": ["assembly kit", "spare caster", "setup guide"],
        "Air Conditioners": ["window exhaust hose", "remote control", "filter kit"],
        "Space Heaters": ["safety guide", "remote control"],
        "Rain Jackets": ["stuff sack", "care card"],
        "Sunscreen": ["usage guide"],
    }[category]


def safety_notes_for(category: str) -> str:
    return {
        "Laptops": "Use only certified chargers and avoid covering ventilation during heavy workloads.",
        "Smartphones": "Do not use swollen batteries or damaged charging cables.",
        "Headphones": "Use moderate volume levels to reduce hearing risk.",
        "Coffee Machines": "Hot surfaces and steam can burn; keep away from children during operation.",
        "Running Shoes": "Replace when outsole grip or midsole cushioning is visibly worn.",
        "Office Chairs": "Assemble fully before use and do not stand on the seat.",
        "Air Conditioners": "Do not block airflow and keep drainage away from electrical connections.",
        "Space Heaters": "Keep at least one meter from fabric, bedding, paper, and curtains during operation.",
        "Rain Jackets": "Reflective trims improve visibility but do not replace dedicated safety lights.",
        "Sunscreen": "Avoid eye contact and discontinue use if irritation occurs.",
    }[category]


def seed_variants_assets_and_specs(db: Session, products: list[models.Product]):
    variants: list[models.ProductVariant] = []
    for product in products:
        product_variants = []
        for variant_index in range(1, random.randint(3, 5)):
            variant = build_variant(product, variant_index)
            db.add(variant)
            variants.append(variant)
            product_variants.append(variant)
        db.flush()

        db.add(
            models.ProductImage(
                product_id=product.product_id,
                url=f"https://placehold.co/900x900/png?text={product.slug}",
                alt_text=f"Primary image of {product.name}",
                position=0,
                is_primary=True,
            )
        )

        for position, variant in enumerate(product_variants, start=1):
            db.add(
                models.ProductImage(
                    product_id=product.product_id,
                    variant_id=variant.variant_id,
                    url=f"https://placehold.co/900x900/png?text={variant.sku}",
                    alt_text=f"{variant.title} product image",
                    position=position,
                    is_primary=False,
                )
            )
            for spec_position, (group_name, name, value, unit) in enumerate(specs_for(product, variant), start=1):
                db.add(
                    models.ProductSpec(
                        product_id=product.product_id,
                        variant_id=variant.variant_id,
                        group_name=group_name,
                        name=name,
                        value=str(value),
                        unit=unit,
                        position=spec_position,
                    )
                )

        seed_reviews(db, product, product_variants)
        seed_competitor_prices(db, product, product_variants)
    db.commit()
    return variants


def build_variant(product: models.Product, index: int) -> models.ProductVariant:
    category = product.category or ""
    color = random.choice(COLORS)
    base_price = float(product.price)
    option_values: dict[str, str | int | float] = {"color": color}
    kwargs: dict = {}

    if category == "Laptops":
        ram = random.choice([8, 16, 32])
        storage = random.choice([256, 512, 1024])
        processor = random.choice(["Intel Core Ultra 5", "Intel Core Ultra 7", "AMD Ryzen 7", "Apple M-series compatible"])
        kwargs.update(
            ram_gb=ram,
            storage_gb=storage,
            storage_type="SSD",
            processor=processor,
            gpu=random.choice(["Integrated", "RTX 4050", "RTX 4060", "Radeon 780M"]),
            display_size=random.choice(["13.3 inch", "14 inch", "15.6 inch", "16 inch"]),
            battery_life_hours=money(random.uniform(8, 16)),
        )
        option_values.update({"ram_gb": ram, "storage_gb": storage, "processor": processor})
        price_factor = 1 + (ram - 8) * 0.035 + (storage / 1024) * 0.12
    elif category == "Smartphones":
        storage = random.choice([128, 256, 512])
        kwargs.update(storage_gb=storage, storage_type="UFS", display_size=random.choice(["6.1 inch", "6.5 inch", "6.8 inch"]))
        option_values.update({"storage_gb": storage})
        price_factor = 1 + (storage / 512) * 0.16
    elif category == "Headphones":
        kwargs.update(battery_life_hours=money(random.uniform(18, 42)), material=random.choice(["vegan leather", "mesh", "silicone"]))
        option_values.update({"fit": random.choice(["over-ear", "in-ear", "on-ear"])})
        price_factor = random.uniform(0.85, 1.25)
    elif category == "Coffee Machines":
        option_values.update({"water_tank_l": random.choice([0.9, 1.2, 1.8, 2.2]), "milk_system": random.choice(["none", "steam wand", "automatic"])})
        price_factor = random.uniform(0.9, 1.35)
    elif category == "Running Shoes":
        size = random.choice(["EU 39", "EU 40", "EU 41", "EU 42", "EU 43", "EU 44"])
        kwargs.update(size=size, material=random.choice(["engineered mesh", "recycled knit", "water-resistant mesh"]))
        option_values.update({"size": size, "terrain": random.choice(["road", "trail", "mixed"])})
        price_factor = random.uniform(0.9, 1.15)
    elif category == "Air Conditioners":
        btu = random.choice([7000, 9000, 12000, 14000])
        option_values.update({"cooling_btu": btu, "room_size_m2": random.choice([18, 24, 32, 40]), "energy_class": random.choice(["A", "A+", "A++"])})
        price_factor = 0.85 + (btu / 14000) * 0.45
    elif category == "Space Heaters":
        watts = random.choice([800, 1200, 1500, 2000])
        option_values.update({"wattage": watts, "heater_type": random.choice(["ceramic", "oil-filled", "infrared", "fan"])})
        price_factor = 0.8 + (watts / 2000) * 0.35
    elif category == "Rain Jackets":
        size = random.choice(["XS", "S", "M", "L", "XL"])
        kwargs.update(size=size, material=random.choice(["2.5-layer recycled nylon", "ripstop polyester", "waterproof breathable shell"]))
        option_values.update({"waterproof_rating_mm": random.choice([8000, 10000, 15000, 20000]), "packable": random.choice(["yes", "no"])})
        price_factor = random.uniform(0.85, 1.28)
    elif category == "Sunscreen":
        size = random.choice(["50 ml", "100 ml", "200 ml"])
        kwargs.update(size=size)
        option_values.update({"spf": random.choice([30, 50, 50]), "skin_type": random.choice(["sensitive", "normal", "kids", "sport"]), "water_resistant": random.choice(["yes", "no"])})
        price_factor = random.uniform(0.8, 1.4)
    else:
        kwargs.update(material=random.choice(["mesh", "fabric", "vegan leather"]), size=random.choice(["standard", "tall", "compact"]))
        option_values.update({"lumbar_support": random.choice(["basic", "adjustable", "dynamic"])})
        price_factor = random.uniform(0.85, 1.3)

    price = base_price * price_factor
    return models.ProductVariant(
        product_id=product.product_id,
        sku=f"{product.sku}-V{index}",
        title=f"{product.name} - {color} Variant {index}",
        color=color,
        option_values=option_values,
        price=money(price),
        cost=money(price * random.uniform(0.48, 0.7)),
        currency="EUR",
        barcode=f"40{random.randint(100000000000, 999999999999)}",
        is_active=True,
        created_at=utcnow(),
        updated_at=utcnow(),
        **kwargs,
    )


def specs_for(product: models.Product, variant: models.ProductVariant):
    category = product.category or ""
    common = [
        ("Support", "Warranty", f"{product.warranty_months} months", None),
        ("Support", "Return window", f"{product.return_window_days} days", None),
        ("General", "Best for", ", ".join(product.use_cases or []), None),
    ]
    if category == "Laptops":
        return [
            ("Performance", "RAM", variant.ram_gb, "GB"),
            ("Performance", "Processor", variant.processor, None),
            ("Performance", "GPU", variant.gpu, None),
            ("Storage", "Storage", variant.storage_gb, "GB"),
            ("Display", "Screen size", variant.display_size, None),
            ("Battery", "Battery life", variant.battery_life_hours, "hours"),
            *common,
        ]
    if category == "Smartphones":
        return [
            ("Storage", "Storage", variant.storage_gb, "GB"),
            ("Display", "Screen size", variant.display_size, None),
            ("Camera", "Main camera", random.choice(["48MP", "50MP", "64MP"]), None),
            ("Battery", "Fast charging", random.choice(["30W", "45W", "65W"]), None),
            *common,
        ]
    if category == "Headphones":
        return [
            ("Audio", "Noise cancellation", random.choice(["hybrid ANC", "passive isolation", "adaptive ANC"]), None),
            ("Battery", "Battery life", variant.battery_life_hours, "hours"),
            ("Connectivity", "Bluetooth", random.choice(["5.2", "5.3", "5.4"]), None),
            *common,
        ]
    if category == "Coffee Machines":
        values = variant.option_values or {}
        return [
            ("Brewing", "Pump pressure", random.choice(["15 bar", "19 bar"]), None),
            ("Water", "Tank capacity", values.get("water_tank_l"), "L"),
            ("Milk", "Milk system", values.get("milk_system"), None),
            *common,
        ]
    if category == "Running Shoes":
        values = variant.option_values or {}
        return [
            ("Fit", "Size", variant.size, None),
            ("Terrain", "Recommended terrain", values.get("terrain"), None),
            ("Material", "Upper", variant.material, None),
            ("Ride", "Cushioning", random.choice(["soft", "balanced", "responsive"]), None),
            *common,
        ]
    if category == "Air Conditioners":
        values = variant.option_values or {}
        return [
            ("Cooling", "Cooling capacity", values.get("cooling_btu"), "BTU"),
            ("Room fit", "Recommended room size", values.get("room_size_m2"), "m2"),
            ("Efficiency", "Energy class", values.get("energy_class"), None),
            ("Comfort", "Dehumidification mode", random.choice(["yes", "no"]), None),
            *common,
        ]
    if category == "Space Heaters":
        values = variant.option_values or {}
        return [
            ("Heating", "Wattage", values.get("wattage"), "W"),
            ("Heating", "Heater type", values.get("heater_type"), None),
            ("Safety", "Tip-over protection", "yes", None),
            ("Safety", "Overheat shutoff", "yes", None),
            *common,
        ]
    if category == "Rain Jackets":
        values = variant.option_values or {}
        return [
            ("Weather", "Waterproof rating", values.get("waterproof_rating_mm"), "mm"),
            ("Fit", "Size", variant.size, None),
            ("Material", "Shell material", variant.material, None),
            ("Travel", "Packable", values.get("packable"), None),
            *common,
        ]
    if category == "Sunscreen":
        values = variant.option_values or {}
        return [
            ("Protection", "SPF", values.get("spf"), None),
            ("Skin", "Skin type", values.get("skin_type"), None),
            ("Water", "Water resistant", values.get("water_resistant"), None),
            ("Size", "Volume", variant.size, None),
            *common,
        ]
    return [
        ("Ergonomics", "Lumbar support", (variant.option_values or {}).get("lumbar_support"), None),
        ("Material", "Cover material", variant.material, None),
        ("Fit", "Size", variant.size, None),
        ("Adjustment", "Armrest adjustment", random.choice(["2D", "3D", "4D"]), None),
        *common,
    ]


def seed_reviews(db: Session, product: models.Product, variants: list[models.ProductVariant]) -> None:
    review_templates = [
        ("Great daily choice", "The product matched the description and the setup was straightforward.", "positive"),
        ("Good but check fit", "Works well, but customers should compare the variant specs before ordering.", "neutral"),
        ("Strong value", "Performance and build quality are convincing for the current price.", "positive"),
        ("Support answered my question", "The detailed specs made it easy to confirm compatibility before purchase.", "positive"),
    ]
    for _ in range(random.randint(3, 7)):
        title, body, sentiment = random.choice(review_templates)
        db.add(
            models.ProductReview(
                product_id=product.product_id,
                variant_id=random.choice(variants).variant_id,
                rating=random.choices([3, 4, 5], weights=[1, 5, 8], k=1)[0],
                title=title,
                body=f"{body} Product: {product.name}. Best use cases: {', '.join(product.use_cases or [])}.",
                sentiment=sentiment,
                created_at=utcnow() - timedelta(days=random.randint(1, 150)),
            )
        )


def seed_competitor_prices(db: Session, product: models.Product, variants: list[models.ProductVariant]) -> None:
    for variant in random.sample(variants, k=min(len(variants), 2)):
        for competitor in random.sample(COMPETITORS, k=3):
            price = float(variant.price) * random.uniform(0.92, 1.12)
            db.add(
                models.CompetitorPrice(
                    product_id=product.product_id,
                    variant_id=variant.variant_id,
                    competitor_name=competitor,
                    competitor_product_url=f"https://example.com/{competitor.lower()}/{variant.sku.lower()}",
                    price=money(price),
                    currency="EUR",
                    observed_at=utcnow() - timedelta(days=random.randint(0, 21)),
                )
            )


def seed_warehouses(db: Session, count: int):
    candidates = [
        ("WH-MUC", "Munich Fulfillment Branch", "Munich", "80331", "Sonnenstrasse 12", "Bavaria", "Germany"),
        ("WH-BER", "Berlin Customer & Fulfillment Hub", "Berlin", "10115", "Invalidenstrasse 45", "Berlin", "Germany"),
        ("WH-FRA", "Frankfurt Distribution Branch", "Frankfurt am Main", "60311", "Zeil 88", "Hesse", "Germany"),
        ("WH-HAM", "Hamburg North Warehouse", "Hamburg", "20095", "Moenckebergstrasse 21", "Hamburg", "Germany"),
        ("WH-CGN", "Cologne Returns & Service Branch", "Cologne", "50667", "Schildergasse 33", "North Rhine-Westphalia", "Germany"),
        ("WH-STR", "Stuttgart South Fulfillment", "Stuttgart", "70173", "Koenigstrasse 10", "Baden-Wuerttemberg", "Germany"),
    ]
    warehouses = [
        models.Warehouse(
            code=code,
            name=name,
            city=city,
            postal_code=postal_code,
            street_address=street_address,
            region=region,
            country=country,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        for code, name, city, postal_code, street_address, region, country in candidates[:count]
    ]
    db.add_all(warehouses)
    db.commit()
    return warehouses


def seed_inventory(db: Session, variants: list[models.ProductVariant], warehouses):
    rows = []
    for variant in variants:
        base = random.randint(15, 260)
        reorder_point = random.randint(8, 55)
        for warehouse in warehouses:
            stock = max(0, int(random.gauss(base, max(4, base * 0.28))))
            rows.append(
                models.Inventory(
                    product_id=variant.product_id,
                    variant_id=variant.variant_id,
                    warehouse_id=warehouse.warehouse_id,
                    stock_on_hand=stock,
                    reorder_point=reorder_point,
                    updated_at=utcnow(),
                )
            )
    db.add_all(rows)
    db.commit()
    return rows


def seed_sales_and_returns(db: Session, variants: list[models.ProductVariant], warehouses, sales_count: int, days: int, return_rate: float):
    now = utcnow()
    start = now - timedelta(days=days)
    top_variants = set(variant.variant_id for variant in variants[: max(10, len(variants) // 5)])
    weights = [8.0 if variant.variant_id in top_variants else 1.0 for variant in variants]
    warehouse_ids = [warehouse.warehouse_id for warehouse in warehouses]

    sales = []
    for _ in range(sales_count):
        variant = random.choices(variants, weights=weights, k=1)[0]
        channel = random.choices(CHANNELS, weights=[0.58, 0.22, 0.08, 0.12], k=1)[0]
        quantity = random.randint(5, 25) if channel == "b2b" else random.randint(1, 4)
        unit_price = float(variant.price) * random.uniform(0.88, 1.04)
        sold_at = start + timedelta(days=int(random.triangular(0, days, days * 0.72)), hours=random.randint(0, 23))
        sales.append(
            models.Sale(
                sold_at=sold_at,
                product_id=variant.product_id,
                variant_id=variant.variant_id,
                warehouse_id=random.choice(warehouse_ids),
                quantity=quantity,
                unit_price=money(unit_price),
                revenue=money(unit_price * quantity),
                channel=channel,
                region=random.choice(REGIONS),
                created_at=now,
            )
        )
    db.add_all(sales)
    db.commit()

    return_count = max(1, int(len(sales) * return_rate))
    reasons = ["damaged", "wrong item", "not compatible", "late delivery", "quality concern", "changed mind"]
    returns = []
    for sale in random.sample(sales, k=return_count):
        returns.append(
            models.Return(
                returned_at=sale.sold_at + timedelta(days=random.randint(1, 30)),
                sale_id=sale.sale_id,
                product_id=sale.product_id,
                variant_id=sale.variant_id,
                quantity=1 if sale.quantity == 1 else random.randint(1, min(2, sale.quantity)),
                reason=random.choice(reasons),
                created_at=utcnow(),
            )
        )
    db.add_all(returns)
    db.commit()
    return len(sales), len(returns)


def seed_market_signals(db: Session, products: list[models.Product], categories: dict[str, models.Category]) -> int:
    count = 0
    signal_types = ["search_trend", "weather_demand", "social_interest", "seasonality", "competitor_promotion"]
    weather_rules = {
        "Air Conditioners": ("heatwave", "Demand rises when forecast temperature stays above 30C for several days."),
        "Space Heaters": ("cold_snap", "Demand rises during freezing nights, gas-price news, and winter home-office periods."),
        "Rain Jackets": ("rain_forecast", "Demand rises before rainy weeks, windy commutes, and spring/autumn travel."),
        "Sunscreen": ("uv_index", "Demand rises with high UV index, summer holidays, beach travel, and outdoor sports."),
        "Running Shoes": ("mild_weather", "Demand rises in mild spring weather and before marathon training seasons."),
        "Coffee Machines": ("cold_morning", "Demand rises during colder mornings and office-return periods."),
        "Headphones": ("travel_season", "Demand rises around commute, holiday travel, and school restart periods."),
        "Laptops": ("back_to_school", "Demand rises before school terms, hiring cycles, and remote-work refresh periods."),
        "Smartphones": ("launch_cycle", "Demand rises around new-device launch windows and holiday gift seasons."),
        "Office Chairs": ("remote_work", "Demand rises during remote-work setup, winter indoor months, and office refresh cycles."),
    }
    for category_name, category in categories.items():
        signal_type, notes = weather_rules.get(category_name, ("seasonality", f"{category_name} seasonal demand signal."))
        for region in REGIONS:
            db.add(
                models.MarketSignal(
                    category_id=category.category_id,
                    signal_type=signal_type if random.random() < 0.7 else random.choice(signal_types),
                    region=region,
                    value=money(random.uniform(0.1, 1.0)),
                    confidence=money(random.uniform(0.55, 0.95)),
                    notes=f"{notes} Region: {region}. Category: {category_name}.",
                    observed_at=utcnow() - timedelta(days=random.randint(0, 14)),
                )
            )
            count += 1
    for product in random.sample(products, k=min(30, len(products))):
        db.add(
            models.MarketSignal(
                product_id=product.product_id,
                category_id=product.category_id,
                signal_type=random.choice(signal_types),
                region=random.choice(REGIONS),
                value=money(random.uniform(0.1, 1.0)),
                confidence=money(random.uniform(0.55, 0.95)),
                notes=f"Product-level signal for {product.name}.",
                observed_at=utcnow() - timedelta(days=random.randint(0, 14)),
            )
        )
        count += 1
    db.commit()
    return count


def main():
    cfg = dict(DEFAULTS)
    cfg["products"] = int(os.getenv("SEED_PRODUCTS", cfg["products"]))
    cfg["warehouses"] = int(os.getenv("SEED_WAREHOUSES", cfg["warehouses"]))
    cfg["sales"] = int(os.getenv("SEED_SALES", cfg["sales"]))
    cfg["days"] = int(os.getenv("SEED_DAYS", cfg["days"]))
    cfg["return_rate"] = float(os.getenv("SEED_RETURN_RATE", cfg["return_rate"]))
    cfg["seed"] = int(os.getenv("SEED_RANDOM", cfg["seed"]))
    random.seed(cfg["seed"])

    with SessionLocal() as db:
        print("Seeding marketplace ProductAI database...")
        ensure_clean_start(db)
        categories = seed_categories(db)
        products, _ = seed_products(db, categories, cfg["products"])
        variants = seed_variants_assets_and_specs(db, products)
        warehouses = seed_warehouses(db, cfg["warehouses"])
        inventory_rows = seed_inventory(db, variants, warehouses)
        sales_count, returns_count = seed_sales_and_returns(
            db,
            variants,
            warehouses,
            sales_count=cfg["sales"],
            days=cfg["days"],
            return_rate=cfg["return_rate"],
        )
        signal_count = seed_market_signals(db, products, categories)

        print(
            "Done "
            f"categories={len(categories)} products={len(products)} variants={len(variants)} "
            f"warehouses={len(warehouses)} inventory={len(inventory_rows)} "
            f"sales={sales_count} returns={returns_count} market_signals={signal_count}"
        )


if __name__ == "__main__":
    main()
