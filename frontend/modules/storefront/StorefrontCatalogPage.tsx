"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import ChatWidget from "../../components/ChatWidget";
import { api } from "../../lib/api";
import type { ListResponse, Product } from "../../lib/types";

export default function StorefrontCatalogPage() {
  const [data, setData] = useState<ListResponse<Product> | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const res = await api.products({ search, limit: 24, offset: 0 });
      setData(res);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load products");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const products = useMemo(() => data?.items ?? [], [data]);

  return (
    <main className="customerPage">
      <nav className="customerNav">
        <Link className="customerBrand" href="/">
          StoreWise AI
        </Link>
        <div className="customerNavLinks">
          <Link href="/merchant">Merchant Portal</Link>
        </div>
      </nav>

      <section className="customerHero">
        <div>
          <p className="welcomeEyebrow">Storefront</p>
          <h1>Find the right product with AI-ready details</h1>
          <p>
            Browse rich product records with descriptions, compatibility notes, use cases,
            warranty context, and seasonal demand-aware catalog data.
          </p>
        </div>
      </section>

      <section className="customerSearch">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search laptops, rain jackets, sunscreen..."
        />
        <button onClick={load} type="button">
          Search
        </button>
      </section>

      <section className="customerStatus">
        {loading ? "Loading products..." : err ? `Error: ${err}` : `Showing ${products.length} products`}
      </section>

      <section className="customerGrid">
        {products.map((product) => (
          <article className="customerProductCard" key={product.product_id}>
            <Link className="customerProductLink" href={`/storefront/products/${product.product_id}`}>
              <div className="customerProductImage">
                <span>{product.category || "Product"}</span>
              </div>
              <div className="customerProductBody">
                <div className="customerProductMeta">
                  {product.brand || "StoreWise"} / {product.category || "Catalog"}
                </div>
                <h2>{product.name}</h2>
                <p>{product.short_description || "Rich product details are available for AI support."}</p>
                <div className="customerProductFooter">
                  <span>
                    {product.currency} {product.price}
                  </span>
                  <span className="customerProductAction">View details</span>
                </div>
              </div>
            </Link>
          </article>
        ))}
      </section>
      <ChatWidget pageContext="Storefront catalog" />
    </main>
  );
}
