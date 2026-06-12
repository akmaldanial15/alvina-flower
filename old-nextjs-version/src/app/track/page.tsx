import { prisma } from '@/lib/prisma';
import Link from 'next/link';

export default async function TrackOrder({ searchParams }: { searchParams: { id?: string } }) {
  const params = await searchParams;
  const id = params.id;
  
  let order = null;
  if (id) {
    order = await prisma.order.findUnique({ where: { id } });
  }

  return (
    <main className="animate-fade-in" style={{ padding: '6rem 2rem', maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
      <h1 className="elegant-title" style={{ fontSize: '3rem', marginBottom: '1rem' }}>
        Track My Order
      </h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '3rem' }}>
        Enter your 13-character order ID starting with 00001 or 00002.
      </p>

      {/* Basic Tracker Form (Client-Side Action via URL Param) */}
      <form action="/track" method="get" className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
        <input 
          type="text" 
          name="id" 
          placeholder="e.g. 00001-A8X92JQK" 
          className="input-field"
          defaultValue={id || ''}
          style={{ marginBottom: '1rem', textAlign: 'center', fontWeight: 'bold', letterSpacing: '2px' }}
        />
        <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Track Order</button>
      </form>

      {id && order && (
        <div className="glass-panel" style={{ padding: '2rem', animation: 'fadeIn 0.5s ease-out' }}>
          <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
            Order ID: {order.id}
          </h3>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', margin: '2rem 0' }}>
            {/* Status Steps Simulation */}
            {['Processing', 'Shipped', 'Delivered'].map((step, index) => {
              const active = order.status === step || (order.status === 'Shipped' && index === 0) || (order.status === 'Delivered');
              return (
                <div key={step} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: active ? 1 : 0.4 }}>
                  <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: active ? 'var(--primary)' : 'var(--text-muted)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '10px' }}>
                    {index + 1}
                  </div>
                  <span style={{ fontSize: '0.9rem', fontWeight: active ? 'bold' : 'normal' }}>{step}</span>
                  {index < 2 && <div style={{ width: '50px', height: '2px', background: active ? 'var(--primary)' : 'var(--text-muted)', margin: '0 10px', marginTop: '-35px' }} />}
                </div>
              );
            })}
          </div>
          <p style={{ color: 'var(--text-muted)' }}>Created on {order.createdAt.toLocaleDateString()}</p>
        </div>
      )}

      {id && !order && (
        <div style={{ padding: '2rem', color: 'red', fontWeight: 'bold' }}>
          Order not found. Please verify your tracking ID.
        </div>
      )}

      <div style={{ marginTop: '3rem' }}>
         <Link href="/" className="btn btn-outline">Back to Home</Link>
      </div>
    </main>
  );
}
