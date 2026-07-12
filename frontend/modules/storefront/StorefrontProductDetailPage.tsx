"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import ChatWidget from "../../components/ChatWidget";
import { api } from "../../lib/api";
import type { ProductDetail, ProductSpec } from "../../lib/types";

function formatPrice(currency: string, value: string | number) {
  return `${currency} ${value}`;
}

function groupSpecs(specs: ProductSpec[]) {
  return specs.reduce<Record<string, ProductSpec[]>>((groups, spec) => {
    const key = spec.group_name || "Details";
    groups[key] = groups[key] || [];
    groups[key].push(spec);
    return groups;
  }, {});
}

export default function StorefrontProductDetailPage() {
  const params = useParams<{ productId: string }>();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setErr("");
      try {
        const data = await api.product(params.productId);
        setProduct(data);
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : "Failed to load product");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [params.productId]);

  const primaryImage = product?.images.find((image) => image.is_primary) ?? product?.images[0];
  const groupedSpecs = useMemo(() => groupSpecs(product?.specs ?? []), [product?.specs]);

  return (
    <main className="customerPage">
      <nav className="customerNav">
        <Link className="customerBrand" href="/">
          ProductAI
        </Link>
        <div className="customerNavLinks">
          <Link href="/storefront">Storefront</Link>
          <Link href="/merchant">Merchant Portal</Link>
        </div>
      </nav>

      {loading && <section className="productDetailStatus">Loading product...</section>}
      {err && <section className="productDetailStatus">Error: {err}</section>}

      {product && (
        <>
          <section className="productDetailHero">
            <div className="productDetailMedia">
              {primaryImage ? (
                <Image
                  className="productDetailImage"
                  src={primaryImage.url}
                  alt={primaryImage.alt_text || product.name}
                  fill
                  sizes="(max-width: 900px) 100vw, 45vw"
                />
              ) : (
                <div className="productDetailPlaceholder">{product.category || "Product"}</div>
              )}
            </div>

            <div className="productDetailSummary">
              <Link className="productDetailBack" href="/storefront">
                Back to storefront
              </Link>
              <div className="customerProductMeta">
                {product.brand || "ProductAI"} / {product.category || "Catalog"}
              </div>
              <h1>{product.name}</h1>
              <p>{product.long_description || product.short_description}</p>

              <div className="productDetailPriceRow">
                <strong>{formatPrice(product.currency, product.price)}</strong>
                <span>Model {product.model_number || product.sku}</span>
              </div>

              <div className="productDetailQuickFacts">
                <span>{product.warranty_months || 12} month warranty</span>
                <span>{product.return_window_days || 30} day returns</span>
                <span>{product.variants.length} variants</span>
              </div>
            </div>
          </section>

          <section className="productDetailLayout">
            <div className="productDetailMain">
              <section className="productDetailSection">
                <h2>Available Variants</h2>
                <div className="variantGrid">
                  {product.variants.map((variant) => (
                    <article className="variantCard" key={variant.variant_id}>
                      <div className="variantTitle">{variant.title}</div>
                      <div className="variantSku">{variant.sku}</div>
                      <div className="variantPrice">{formatPrice(variant.currency, variant.price)}</div>
                      <dl>
                        {variant.color && (
                          <>
                            <dt>Color</dt>
                            <dd>{variant.color}</dd>
                          </>
                        )}
                        {variant.size && (
                          <>
                            <dt>Size</dt>
                            <dd>{variant.size}</dd>
                          </>
                        )}
                        {variant.ram_gb && (
                          <>
                            <dt>RAM</dt>
                            <dd>{variant.ram_gb} GB</dd>
                          </>
                        )}
                        {variant.storage_gb && (
                          <>
                            <dt>Storage</dt>
                            <dd>
                              {variant.storage_gb} GB {variant.storage_type}
                            </dd>
                          </>
                        )}
                      </dl>
                    </article>
                  ))}
                </div>
              </section>

              <section className="productDetailSection">
                <h2>Specifications</h2>
                <div className="specGroupGrid">
                  {Object.entries(groupedSpecs).map(([group, specs]) => (
                    <article className="specGroup" key={group}>
                      <h3>{group}</h3>
                      <dl>
                        {specs.slice(0, 8).map((spec) => (
                          <div key={spec.spec_id}>
                            <dt>{spec.name}</dt>
                            <dd>
                              {spec.value}
                              {spec.unit ? ` ${spec.unit}` : ""}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </article>
                  ))}
                </div>
              </section>

              <section className="productDetailSection">
                <h2>Customer Signals</h2>
                <div className="reviewGrid">
                  {product.reviews.map((review) => (
                    <article className="reviewCard" key={review.review_id}>
                      <div className="reviewRating">{"*".repeat(review.rating)}</div>
                      <h3>{review.title}</h3>
                      <p>{review.body}</p>
                    </article>
                  ))}
                </div>
              </section>
            </div>

            <aside className="productDetailAside">
              <section>
                <h2>Support Notes</h2>
                <dl>
                  <dt>Best for</dt>
                  <dd>{product.use_cases?.join(", ") || "General product use"}</dd>
                  <dt>Audience</dt>
                  <dd>{product.target_audience || "Customers comparing product fit"}</dd>
                  <dt>Compatibility</dt>
                  <dd>{product.compatibility_notes || "No special compatibility notes."}</dd>
                  <dt>Care</dt>
                  <dd>{product.care_instructions || "Follow standard care instructions."}</dd>
                  <dt>Included</dt>
                  <dd>{product.included_accessories?.join(", ") || "Standard package contents"}</dd>
                  <dt>Safety</dt>
                  <dd>{product.safety_notes || "Use according to product instructions."}</dd>
                </dl>
              </section>
            </aside>
          </section>
        </>
      )}

      <ChatWidget pageContext={product ? `Product: ${product.name}` : "Product detail"} />
    </main>
  );
}
