import 'dotenv/config'
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  await prisma.product.deleteMany()
  await prisma.promotion.deleteMany()

  const p1 = await prisma.product.create({
    data: {
      name: 'Pastel Dream Bouquet',
      description: 'An extremely elegant and premium bouquet of pastel pink and white roses, softly lit. Perfect for an exquisite luxury gift.',
      price: 249.00,
      image: '/images/flower1.png',
      category: 'Bouquets',
      budget: 'High',
      use: 'Anniversary'
    }
  })

  const p2 = await prisma.product.create({
    data: {
      name: 'Luxury Rose Box',
      description: 'A luxury white box containing perfect pastel pink roses and orchids, elegantly tied with a silk ribbon.',
      price: 189.00,
      image: '/images/flower2.png',
      category: 'Boxed Flowers',
      budget: 'Medium',
      use: 'Birthday'
    }
  })

  const p3 = await prisma.product.create({
    data: {
      name: 'Spring Blossom Basket',
      description: 'A beautiful hand-woven basket filled with white and blush pink tulips, peonies, and subtle greenery.',
      price: 139.00,
      image: '/images/flower3.png',
      category: 'Baskets',
      budget: 'Low',
      use: 'Get Well'
    }
  })

  const p4 = await prisma.product.create({
    data: {
      name: 'Alvina Signature Bloom',
      description: 'Our signature collection, an elegant mix of roses and delicate baby breath flowers in pastel pink wrap.',
      price: 299.00,
      image: '/images/flower1.png', // Reusing
      category: 'Bouquets',
      budget: 'High',
      use: 'Wedding'
    }
  })

  // Create Promotion
  await prisma.promotion.create({
    data: {
      title: 'Spring Special Sale!',
      description: 'Get 15% off all pastel bouquets this month with code SPRING15.',
      discount: '15%',
      bannerImage: null,
      isActive: true
    }
  })

  console.log('Seeded database successfully!')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
