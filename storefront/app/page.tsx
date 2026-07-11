import Image from "next/image";
import {
  ArrowRight,
  BadgeCheck,
  Headphones,
  Heart,
  Leaf,
  Menu,
  Search,
  ShoppingBag,
  Sparkles,
  Truck,
  UserRound,
} from "lucide-react";

const categories = [
  { name: "Home", detail: "Quiet upgrades", tone: "sage", icon: Leaf },
  { name: "Tech", detail: "Useful by design", tone: "blue", icon: Sparkles },
  { name: "Carry", detail: "Made to move", tone: "coral", icon: ShoppingBag },
  { name: "Wellness", detail: "Everyday rituals", tone: "yellow", icon: Heart },
];

const products = [
  { name: "Field Bottle", category: "Carry", price: "EUR 34", crop: "bottle", tag: "Bestseller" },
  { name: "Hush Speaker", category: "Tech", price: "EUR 89", crop: "speaker", tag: "New" },
  { name: "Hearth Lamp", category: "Home", price: "EUR 119", crop: "lamp", tag: "" },
  { name: "Daylight Tote", category: "Carry", price: "EUR 42", crop: "tote", tag: "Low stock" },
];

export default function Home() {
  return (
    <main>
      <div className="announcement">
        <span>Free delivery on orders over EUR 60</span>
        <a href="#featured">Shop new arrivals <ArrowRight size={14} /></a>
      </div>

      <header className="siteHeader">
        <a className="brand" href="#" aria-label="Morrow Market home">
          <span className="brandMark">M</span>
          <span>Morrow Market</span>
        </a>
        <nav className="desktopNav" aria-label="Main navigation">
          <a href="#featured">New in</a>
          <a href="#categories">Shop</a>
          <a href="#story">Our story</a>
        </nav>
        <div className="headerActions">
          <button className="iconButton" aria-label="Search" title="Search"><Search /></button>
          <button className="iconButton desktopOnly" aria-label="Account" title="Account"><UserRound /></button>
          <button className="bagButton" aria-label="Shopping bag">
            <ShoppingBag />
            <span className="desktopOnly">Bag</span>
            <b>0</b>
          </button>
          <button className="iconButton mobileOnly" aria-label="Open menu" title="Menu"><Menu /></button>
        </div>
      </header>

      <section className="hero">
        <Image
          src="/images/morrow-hero.png"
          alt="A curated collection of Morrow Market home and everyday products"
          fill
          priority
          sizes="100vw"
          className="heroImage"
        />
        <div className="heroShade" />
        <div className="heroContent">
          <p className="eyebrow">The spring edit</p>
          <h1>Everyday goods,<br />considered.</h1>
          <p className="heroCopy">
            Useful objects chosen for how they work, how they last, and how they make the day feel.
          </p>
          <a className="primaryButton" href="#featured">
            Explore the collection <ArrowRight size={18} />
          </a>
        </div>
        <div className="heroNote">
          <span>01</span>
          <p><b>Fresh foundations</b><br />A lighter way to reset your space.</p>
        </div>
      </section>

      <section className="categorySection" id="categories">
        <div className="sectionHeading">
          <div>
            <p className="eyebrow dark">Browse by room and rhythm</p>
            <h2>Find your everyday essential</h2>
          </div>
          <a href="#featured">View all categories <ArrowRight size={17} /></a>
        </div>
        <div className="categoryGrid">
          {categories.map(({ name, detail, tone, icon: Icon }) => (
            <a className={`categoryTile ${tone}`} href="#featured" key={name}>
              <span className="categoryIcon"><Icon size={26} strokeWidth={1.7} /></span>
              <span>
                <b>{name}</b>
                <small>{detail}</small>
              </span>
              <ArrowRight size={20} />
            </a>
          ))}
        </div>
      </section>

      <section className="featuredSection" id="featured">
        <div className="sectionHeading">
          <div>
            <p className="eyebrow dark">Morrow favourites</p>
            <h2>Good choices, made simple</h2>
          </div>
          <a href="#">Shop all products <ArrowRight size={17} /></a>
        </div>
        <div className="productGrid">
          {products.map((product) => (
            <article className="productCard" key={product.name}>
              <div className={`productImage ${product.crop}`}>
                <Image
                  src="/images/morrow-hero.png"
                  alt={product.name}
                  fill
                  sizes="(max-width: 700px) 50vw, 25vw"
                />
                {product.tag && <span className="productTag">{product.tag}</span>}
                <button className="heartButton" aria-label={`Save ${product.name}`} title="Save item">
                  <Heart size={19} />
                </button>
              </div>
              <div className="productMeta">
                <div>
                  <small>{product.category}</small>
                  <h3>{product.name}</h3>
                </div>
                <b>{product.price}</b>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="storyBand" id="story">
        <div>
          <p className="eyebrow">Why Morrow</p>
          <h2>Less noise.<br />More good stuff.</h2>
        </div>
        <p>
          We edit down the endless shelf to objects that earn their place. Clear materials,
          fair value, and support from a real team when you need it.
        </p>
        <a className="textButton" href="#">Meet Morrow <ArrowRight size={18} /></a>
      </section>

      <section className="serviceStrip" aria-label="Store services">
        <div><Truck /><span><b>Easy delivery</b><small>Tracked from our door to yours</small></span></div>
        <div><BadgeCheck /><span><b>30-day returns</b><small>Simple, fair, and fuss-free</small></span></div>
        <div><Headphones /><span><b>Human support</b><small>AI-assisted help is coming next</small></span></div>
      </section>

      <footer>
        <a className="brand footerBrand" href="#">
          <span className="brandMark">M</span>
          <span>Morrow Market</span>
        </a>
        <p>Thoughtful goods for the shape of everyday life.</p>
        <small>© 2026 Morrow Market</small>
      </footer>
    </main>
  );
}
