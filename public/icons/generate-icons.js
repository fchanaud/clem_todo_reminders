// This is a simple Node.js script to generate placeholder icons
// To use it, you'll need to have Node.js installed and run:
// npm install canvas
// node generate-icons.js

const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');

// Icon sizes to generate
const sizes = [
  { name: 'icon-192x192.png', width: 192, height: 192 },
  { name: 'icon-512x512.png', width: 512, height: 512 },
  { name: 'icon-maskable-192x192.png', width: 192, height: 192, maskable: true },
  { name: 'icon-maskable-512x512.png', width: 512, height: 512, maskable: true },
  { name: 'apple-icon-180.png', width: 180, height: 180 },
];

// Function to create an icon
function createIcon(name, width, height, maskable = false) {
  const canvas = createCanvas(width, height);
  const context = canvas.getContext('2d');

  // Create background
  context.fillStyle = '#4f46e5'; // Indigo color
  context.fillRect(0, 0, width, height);

  // For maskable icons, we need to leave a safe zone
  const iconSize = maskable ? Math.min(width, height) * 0.6 : Math.min(width, height) * 0.8;
  const x = (width - iconSize) / 2;
  const y = (height - iconSize) / 2;

  // Create "CT" text for "Clem Todo"
  context.fillStyle = '#ffffff';
  context.font = `bold ${iconSize * 0.7}px Arial`;
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText('CT', width / 2, height / 2);

  // Save the image
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(path.join(__dirname, name), buffer);
  
  console.log(`Created ${name}`);
}

// Create directory if it doesn't exist
if (!fs.existsSync(__dirname)) {
  fs.mkdirSync(__dirname, { recursive: true });
}

// Generate all icons
sizes.forEach(size => {
  createIcon(size.name, size.width, size.height, size.maskable);
});

console.log('All icons generated! Place them in your public/icons directory.');
console.log('Note: For production, you should replace these with proper designed icons.'); 