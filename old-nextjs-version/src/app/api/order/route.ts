import { prisma } from '@/lib/prisma';
import { NextResponse } from 'next/server';

function generateOrderId() {
  const prefix = Math.random() > 0.5 ? '00001' : '00002';
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let randomString = '';
  for (let i = 0; i < 8; i++) {
    randomString += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `${prefix}-${randomString}`; // Minimum 13 chars long
}

export async function POST(req: Request) {
  try {
    const { productId, price } = await req.json();

    const orderId = generateOrderId();
    
    // Simulate user details if needed, for simulation we just create the order
    const order = await prisma.order.create({
      data: {
        id: orderId,
        totalAmount: price,
        status: 'Processing',
        products: JSON.stringify([{ productId, quantity: 1 }])
      }
    });

    return NextResponse.json({ success: true, orderId: order.id });
  } catch (error) {
    console.error('Order creation error:', error);
    return NextResponse.json({ success: false, error: 'Failed to create order' }, { status: 500 });
  }
}
