import { prisma } from '@/lib/prisma';
import Link from 'next/link';

export default async function AdminDashboard() {
  const orders = await prisma.order.findMany();
  const products = await prisma.product.findMany();
  
  const totalRM = orders.reduce((sum, order) => sum + order.totalAmount, 0);

  // Categorize
  const categorySummary = products.reduce((acc, p) => {
    acc[p.category] = (acc[p.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <main className="animate-fade-in" style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
        <h1 className="elegant-title" style={{ fontSize: '2.5rem' }}>Admin Dashboard</h1>
        <Link href="/" className="btn btn-outline" style={{ fontSize: '0.9rem' }}>Return to Storefront</Link>
      </header>

      {/* Summary Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginBottom: '3rem' }}>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <h3 style={{ color: 'var(--text-muted)' }}>Total Revenue</h3>
          <p style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>RM {totalRM.toFixed(2)}</p>
        </div>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <h3 style={{ color: 'var(--text-muted)' }}>Total Orders</h3>
          <p style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>{orders.length}</p>
        </div>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <h3 style={{ color: 'var(--text-muted)' }}>Products Listed</h3>
          <p style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>{products.length}</p>
        </div>
      </section>

      <section style={{ display: 'flex', gap: '3rem', flexWrap: 'wrap' }}>
        
        {/* Category Breakdown */}
        <div className="glass-panel" style={{ flex: '1 1 300px', padding: '2rem' }}>
          <h2 className="elegant-title" style={{ fontSize: '1.8rem', marginBottom: '1.5rem' }}>Products by Category</h2>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.entries(categorySummary).map(([cat, count]) => (
              <li key={cat} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border)', paddingBottom: '0.5rem' }}>
                <span style={{ fontWeight: '500' }}>{cat}</span>
                <span style={{ color: 'white', background: 'var(--primary)', padding: '2px 10px', borderRadius: '15px', fontSize: '0.8rem' }}>{count}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recent Orders Table */}
        <div className="glass-panel" style={{ flex: '2 1 500px', padding: '2rem' }}>
          <h2 className="elegant-title" style={{ fontSize: '1.8rem', marginBottom: '1.5rem' }}>Recent Orders</h2>
          {orders.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>No orders yet.</p>
          ) : (
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  <th style={{ padding: '10px 0' }}>Order ID</th>
                  <th>Status</th>
                  <th>Amount</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(-5).map(order => (
                  <tr key={order.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 0', fontFamily: 'monospace' }}>{order.id}</td>
                    <td>
                      <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', background: order.status === 'Processing' ? '#FFF3CD' : '#D4EDDA', color: order.status === 'Processing' ? '#856404' : '#155724' }}>
                        {order.status}
                      </span>
                    </td>
                    <td style={{ fontWeight: 'bold' }}>RM {order.totalAmount.toFixed(2)}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{order.createdAt.toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Admin Actions */}
      <section style={{ marginTop: '3rem', textAlign: 'center' }}>
        <button className="btn btn-primary" style={{ margin: '0 10px' }}>Manage Products</button>
        <button className="btn btn-outline" style={{ margin: '0 10px' }}>Edit Promotions</button>
      </section>
    </main>
  );
}
