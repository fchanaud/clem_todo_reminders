# PWA Icons Guide

To make the app work as a Progressive Web App (PWA) on your iPhone, you'll need to generate several icons and splash screens.

## Icons Required

You need to create the following icons in the `public/icons` directory:

1. Basic PWA icons:
   - `icon-192x192.png` (192x192)
   - `icon-512x512.png` (512x512)
   - `icon-maskable-192x192.png` (192x192, with extra padding for maskable format)
   - `icon-maskable-512x512.png` (512x512, with extra padding for maskable format)

2. Apple specific icons:
   - `apple-icon-180.png` (180x180)

3. Apple splash screens (for various device sizes):
   - `apple-splash-2048-2732.jpg` 
   - `apple-splash-1668-2388.jpg`
   - `apple-splash-1536-2048.jpg`
   - `apple-splash-1242-2688.jpg`
   - `apple-splash-1125-2436.jpg`
   - `apple-splash-828-1792.jpg`
   - `apple-splash-750-1334.jpg`
   - `apple-splash-640-1136.jpg`

## Easy Way to Generate Icons

The easiest way to generate all these icons is to use an online tool like:

1. **PWA Asset Generator**: https://www.pwabuilder.com/imageGenerator
2. **PWA Image Generator**: https://tools.crawlink.com/tools/pwa-icon-generator/
3. **App Icon Generator**: https://appicon.co/

Start with a high-quality square image (at least 1024x1024 pixels) for the best results.

## Manual Generation

If you prefer to generate these manually:

1. Create a base image (your app logo) in a square format
2. Use tools like Adobe Photoshop, GIMP, or online resizers to create all required sizes
3. For maskable icons, make sure your main content is within the "safe zone" (central 80% of the image)

## Next Steps

1. Generate all required icons
2. Place them in the `/public/icons/` directory
3. Rebuild and deploy your application
4. Test on your iPhone by adding to home screen

## Testing PWA Installation

1. Open your app in Safari on iPhone
2. Tap the share button
3. Scroll down and tap "Add to Home Screen"
4. Name your app and tap "Add"

Your app should now open in full screen mode as a standalone app on your iPhone! 