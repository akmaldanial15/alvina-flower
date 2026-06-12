import { prisma } from '@/lib/prisma';
import Link from 'next/link';

export default async function ProductsPage() {
  const products = await prisma.product.findMany();

  return (
    <main className="animate-fade-in" style={{ padding: '4rem 2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 className="elegant-title" style={{ fontSize: '3rem', marginBottom: '2rem', textAlign: 'center' }}>
        Our Collection
      </h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '2rem' }}>
        {products.map((product) => (
          <div key={product.id} className="glass" style={{ overflow: 'hidden' }}>
            <div style={{ height: '300px', background: `url(${product.image}) center/cover no-repeat` }} />
            <div style={{ padding: '1.5rem' }}>
              <h3 className="elegant-title" style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{product.name}</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1rem', fontSize: '0.9rem' }}>{product.category} • {product.use}</p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 'bold', fontSize: '1.2rem', color: 'var(--text-main)' }}>RM {product.price.toFixed(2)}</span>
                <Link href={`/products/${product.id}`} className="btn btn-outline">Details</Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
