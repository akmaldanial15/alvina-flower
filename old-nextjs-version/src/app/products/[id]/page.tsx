import { prisma } from '@/lib/prisma';
import { notFound } from 'next/navigation';
import OrderButton from './OrderButton';
import Link from 'next/link';

export default async function ProductDetails({ params }: { params: { id: string } }) {
  const { id } = await params;
  const product = await prisma.product.findUnique({
    where: { id }
  });

  if (!product) return notFound();

  return (
    <main className="animate-fade-in" style={{ padding: '4rem 2rem', maxWidth: '1000px', margin: '0 auto', display: 'flex', gap: '4rem', alignItems: 'center', flexWrap: 'wrap' }}>
      
      {/* Product Image */}
      <div style={{ flex: '1 1 400px' }} className="glass-panel">
        <img 
          src={product.image} 
          alt={product.name} 
          style={{ width: '100%', height: 'auto', borderRadius: 'var(--radius-lg)' }} 
        />
      </div>

      {/* Product Information */}
      <div style={{ flex: '1 1 400px' }}>
        <h1 className="elegant-title" style={{ fontSize: '3rem', marginBottom: '1rem' }}>
          {product.name}
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.2rem', marginBottom: '1.5rem', lineHeight: '1.6' }}>
          {product.description}
        </p>
        
        <div style={{ marginBottom: '2rem' }}>
          <span style={{ display: 'inline-block', background: 'rgba(248, 200, 216, 0.3)', padding: '6px 16px', borderRadius: '20px', fontSize: '0.9rem', marginRight: '10px' }}>
            {product.category}
          </span>
          <span style={{ display: 'inline-block', background: 'rgba(248, 200, 216, 0.3)', padding: '6px 16px', borderRadius: '20px', fontSize: '0.9rem' }}>
            {product.use}
          </span>
        </div>
        
        <h2 style={{ fontSize: '2.5rem', marginBottom: '1.5rem', color: 'var(--text-main)', fontWeight: 'bold' }}>
          RM {product.price.toFixed(2)}
        </h2>

        {/* Client-Side Ordering Flow */}
        <OrderButton productId={product.id} price={product.price} />

        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <Link href="/products" className="btn btn-outline">Back to Products</Link>
        </div>
      </div>
      
    </main>
  );
}
