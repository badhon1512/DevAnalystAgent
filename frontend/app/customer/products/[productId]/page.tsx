import { redirect } from "next/navigation";

export default function CustomerProductRedirectPage({ params }: { params: { productId: string } }) {
  redirect(`/storefront/products/${params.productId}`);
}
