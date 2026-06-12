import { prisma } from '@/lib/prisma';
import Link from 'next/link';

export default async function Home() {
  const promotions = await prisma.promotion.findMany({ where: { isActive: true } });
  const products = await prisma.product.findMany({ take: 6 });

  return (
    <main className="animate-fade-in">
      {/* Top Promotional Banner */}
      {promotions.length > 0 && (
        <div style={{ background: 'var(--primary)', color: 'white', padding: '10px 0', textAlign: 'center', fontWeight: 'bold' }}>
          {promotions[0].title} - {promotions[0].description}
        </div>
      )}

      {/* Hero Section */}
      <section style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <h1 className="elegant-title" style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>
          Alvina Flower
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.2rem', marginBottom: '2rem' }}>
          Elegant creations for your special moments
        </p>
        
        {/* Search & Filter Mockup */}
        <div className="glass-panel" style={{ maxWidth: '600px', margin: '0 auto', padding: '1.5rem', display: 'flex', gap: '10px' }}>
          <input type="text" placeholder="Search by type, budget, occasion..." className="input-field" />
          <Link href="/products" className="btn btn-primary">Search</Link>
        </div>
      </section>

      {/* Featured Products */}
      <section style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        <h2 className="elegant-title" style={{ fontSize: '2.5rem', marginBottom: '2rem', textAlign: 'center' }}>
          Featured Collection
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '2rem' }}>
          {products.map((product) => (
            <div key={product.id} className="glass" style={{ transition: 'transform 0.3s ease', cursor: 'pointer', overflow: 'hidden' }}>
              <div style={{ height: '300px', background: `url(${product.image}) center/cover no-repeat` }} />
              <div style={{ padding: '1.5rem' }}>
                <h3 className="elegant-title" style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{product.name}</h3>
                <p style={{ color: 'var(--text-muted)', marginBottom: '1rem', fontSize: '0.9rem' }}>{product.category} • {product.use}</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'bold', fontSize: '1.2rem', color: 'var(--text-main)' }}>RM {product.price.toFixed(2)}</span>
                  <Link href={`/products/${product.id}`} className="btn btn-outline">View</Link>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div style={{ textAlign: 'center', marginTop: '3rem' }}>
          <Link href="/products" className="btn btn-primary" style={{ padding: '12px 32px' }}>
            View All Blooms
          </Link>
        </div>
      </section>

      {/* Floating WhatsApp contact */}
      <a 
        href="http://wa.me/60134311045" 
        target="_blank" 
        rel="noopener noreferrer"
        style={{
          position: 'fixed', bottom: '30px', right: '30px', 
          background: '#25D366', color: 'white', padding: '15px', 
          borderRadius: '50%', boxShadow: 'var(--shadow-lg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: '60px', height: '60px', zIndex: 1000
        }}
        title="Chat with us on WhatsApp"
      >
        <svg fill="currentColor" viewBox="0 0 24 24" style={{ width: '35px', height: '35px' }}>
          <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.347-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.876 1.213 3.074.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
        </svg>
      </a>
    </main>
  );
}
