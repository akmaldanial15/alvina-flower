'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function OrderButton({ productId, price }: { productId: string; price: number }) {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleOrder = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ productId, price })
      });
      const data = await res.json();
      if (data.success) {
        // Redirect to track page with order ID
        router.push(`/track?id=${data.orderId}`);
      } else {
        alert('Failed to place order.');
      }
    } catch (e) {
      console.error(e);
      alert('Error placing order.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button 
      className="btn btn-primary" 
      onClick={handleOrder} 
      disabled={loading}
      style={{ width: '100%', padding: '16px', fontSize: '1.2rem', marginTop: '1rem' }}
    >
      {loading ? 'Processing...' : 'Order Now'}
    </button>
  );
}
