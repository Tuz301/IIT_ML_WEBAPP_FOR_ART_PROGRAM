/**
 * CDN Configuration Module
 * 
 * This module provides configuration and utilities for serving static assets
 * through a Content Delivery Network (CDN) in production environments.
 */

export interface CDNConfig {
  /** Whether CDN is enabled */
  enabled: boolean;
  /** Base URL for CDN (e.g., https://cdn.yourdomain.com) */
  baseUrl: string;
  /** CDN URLs for different asset types */
  assets: {
    images: string;
    fonts: string;
    css: string;
    js: string;
  };
  /** Cache duration for different asset types (in seconds) */
  cacheDuration: {
    images: number;
    fonts: number;
    css: number;
    js: number;
  };
}

/**
 * Get CDN configuration from environment variables
 */
export function getCDNConfig(): CDNConfig {
  const enabled = import.meta.env.VITE_CDN_ENABLED === 'true';
  const baseUrl = import.meta.env.VITE_CDN_URL || '';

  return {
    enabled,
    baseUrl,
    assets: {
      images: import.meta.env.VITE_CDN_IMAGES_URL || (enabled ? `${baseUrl}/images/` : '/static/images/'),
      fonts: import.meta.env.VITE_CDN_FONTS_URL || (enabled ? `${baseUrl}/fonts/` : '/static/fonts/'),
      css: import.meta.env.VITE_CDN_CSS_URL || (enabled ? `${baseUrl}/css/` : '/static/css/'),
      js: import.meta.env.VITE_CDN_JS_URL || (enabled ? `${baseUrl}/js/` : '/static/js/'),
    },
    cacheDuration: {
      images: parseInt(import.meta.env.VITE_CDN_CACHE_IMAGES || '31536000', 10), // 1 year
      fonts: parseInt(import.meta.env.VITE_CDN_CACHE_FONTS || '31536000', 10), // 1 year
      css: parseInt(import.meta.env.VITE_CDN_CACHE_CSS || '86400', 10), // 1 day
      js: parseInt(import.meta.env.VITE_CDN_CACHE_JS || '86400', 10), // 1 day
    },
  };
}

/**
 * Get full CDN URL for an asset path
 * 
 * @param path - Relative path to the asset (e.g., '/static/images/logo.png')
 * @returns Full CDN URL if enabled, otherwise returns the original path
 * 
 * @example
 * ```ts
 * getAssetUrl('/static/images/logo.png')
 * // Returns: 'https://cdn.yourdomain.com/images/logo.png' (if CDN enabled)
 * // Returns: '/static/images/logo.png' (if CDN disabled)
 * ```
 */
export function getAssetUrl(path: string): string {
  const config = getCDNConfig();
  
  if (!config.enabled || !config.baseUrl) {
    return path;
  }
  
  // Remove leading slash and 'static/' prefix if present
  const cleanPath = path
    .replace(/^\/+/, '')
    .replace(/^static\//, '');
  
  return `${config.baseUrl}/${cleanPath}`;
}

/**
 * Get CDN URL for an image
 * 
 * @param filename - Image filename (e.g., 'logo.png')
 * @returns Full CDN URL for the image
 */
export function getImageUrl(filename: string): string {
  const config = getCDNConfig();
  const baseUrl = config.assets.images;
  return `${baseUrl}${filename}`;
}

/**
 * Get CDN URL for a font
 * 
 * @param filename - Font filename (e.g., 'inter.woff2')
 * @returns Full CDN URL for the font
 */
export function getFontUrl(filename: string): string {
  const config = getCDNConfig();
  const baseUrl = config.assets.fonts;
  return `${baseUrl}${filename}`;
}

/**
 * Get CDN URL for a CSS file
 * 
 * @param filename - CSS filename (e.g., 'main.css')
 * @returns Full CDN URL for the CSS file
 */
export function getCssUrl(filename: string): string {
  const config = getCDNConfig();
  const baseUrl = config.assets.css;
  return `${baseUrl}${filename}`;
}

/**
 * Get CDN URL for a JavaScript file
 * 
 * @param filename - JavaScript filename (e.g., 'app.js')
 * @returns Full CDN URL for the JavaScript file
 */
export function getJsUrl(filename: string): string {
  const config = getCDNConfig();
  const baseUrl = config.assets.js;
  return `${baseUrl}${filename}`;
}

/**
 * Generate cache-busting URL with version or hash
 * 
 * @param path - Original asset path
 * @param version - Version string or content hash
 * @returns URL with cache-busting parameter
 * 
 * @example
 * ```ts
 * getCacheBustingUrl('/static/app.js', '1.2.3')
 * // Returns: '/static/app.js?v=1.2.3'
 * ```
 */
export function getCacheBustingUrl(path: string, version: string): string {
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}v=${version}`;
}

/**
 * Preload critical assets for faster page load
 * 
 * @param assets - Array of asset URLs to preload
 * 
 * @example
 * ```ts
 * preloadAssets([
 *   getCssUrl('critical.css'),
 *   getFontUrl('inter.woff2')
 * ])
 * ```
 */
export function preloadAssets(assets: string[]): void {
  if (typeof document === 'undefined') return;
  
  assets.forEach(asset => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = asset;
    
    // Determine as attribute based on file extension
    if (asset.endsWith('.css')) {
      link.as = 'style';
    } else if (asset.endsWith('.js')) {
      link.as = 'script';
    } else if (asset.match(/\.(woff|woff2|ttf|otf|eot)$/)) {
      link.as = 'font';
      link.crossOrigin = 'anonymous';
    } else if (asset.match(/\.(jpg|jpeg|png|webp|gif|svg)$/)) {
      link.as = 'image';
    }
    
    document.head.appendChild(link);
  });
}

/**
 * Prefetch assets for likely future navigation
 * 
 * @param assets - Array of asset URLs to prefetch
 */
export function prefetchAssets(assets: string[]): void {
  if (typeof document === 'undefined') return;
  
  assets.forEach(asset => {
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = asset;
    document.head.appendChild(link);
  });
}

/**
 * Check if CDN is available and responding
 * 
 * @returns Promise that resolves to true if CDN is available
 */
export async function checkCDNAvailability(): Promise<boolean> {
  const config = getCDNConfig();
  
  if (!config.enabled || !config.baseUrl) {
    return false;
  }
  
  try {
    const response = await fetch(`${config.baseUrl}/health`, {
      method: 'HEAD',
      cache: 'no-store',
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Get asset with fallback to origin if CDN fails
 * 
 * @param cdnUrl - CDN URL for the asset
 * @param fallbackUrl - Origin URL as fallback
 * @returns Promise that resolves to the asset URL that works
 */
export async function getAssetWithFallback(
  cdnUrl: string,
  fallbackUrl: string
): Promise<string> {
  try {
    const response = await fetch(cdnUrl, { method: 'HEAD' });
    if (response.ok) {
      return cdnUrl;
    }
  } catch {
    // CDN failed, use fallback
  }
  return fallbackUrl;
}

// Export singleton config instance
export const cdnConfig = getCDNConfig();
