import { ProductShell } from "@/components/layout/product-shell";
import { SystemDashboard } from "@/components/system/system-dashboard";


export default function Home() {
  return (
    <ProductShell>
      <SystemDashboard />
    </ProductShell>
  );
}

