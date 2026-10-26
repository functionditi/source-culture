import { ImageMagick, initializeImageMagick, MagickFormat, ResourceLimits } from 'npm:@imagemagick/magick-wasm@0.0.45';
import { APIError } from './validation.mjs';

// Use WASM rather than native sharp, which the Edge runtime cannot execute.
// Lazy initialization avoids charging public text requests for image processing.
let initialized: Promise<void> | undefined;
export async function cleanImage(base64: string): Promise<Uint8Array> {
  if (base64.length > 6990508 || !/^[A-Za-z0-9+/]*={0,2}$/.test(base64)) throw new APIError(422, 'Each image must be a valid image smaller than 5 MB.');
  let raw: Uint8Array;
  try { raw = Uint8Array.from(atob(base64), c => c.charCodeAt(0)); }
  catch { throw new APIError(422, 'That file is not a supported image.'); }
  if (!raw.length || raw.length > 5 * 1024 * 1024) throw new APIError(422, 'Each image must be smaller than 5 MB.');
  const jpeg = raw[0] === 255 && raw[1] === 216 && raw[2] === 255;
  const png = raw.slice(0,8).every((b,i) => b === [137,80,78,71,13,10,26,10][i]) && raw.length >= 24;
  const webp = new TextDecoder().decode(raw.slice(0,4)) === 'RIFF' && new TextDecoder().decode(raw.slice(8,12)) === 'WEBP';
  if (!jpeg && !png && !webp) throw new APIError(422, 'Use JPEG, PNG, or WebP.');
  // Inspect dimensions before full decode to reject compressed image bombs.
  const { width, height } = dimensions(raw, jpeg, png);
  if (!width || !height || width * height > 24000000) throw new APIError(422, 'Use an image of at most 24 megapixels.');
  initialized ||= Deno.readFile(new URL(import.meta.resolve('npm:@imagemagick/magick-wasm@0.0.45/magick.wasm')))
    .then(async bytes => {
      await initializeImageMagick(bytes);
      ResourceLimits.memory = 96n * 1024n * 1024n;
      ResourceLimits.maxMemoryRequest = 96n * 1024n * 1024n;
      ResourceLimits.disk = 0n;
      // ImageMagick uses internal temporary images while decoding/encoding.
      ResourceLimits.listLength = 8n;
      ResourceLimits.maxProfileSize = 8n * 1024n * 1024n;
    });
  await initialized;
  try {
    return ImageMagick.read(raw, image => {
      if (!new Set<MagickFormat>([MagickFormat.Jpeg, MagickFormat.Png, MagickFormat.WebP]).has(image.format)) throw new APIError(422, 'Use JPEG, PNG, or WebP.');
      image.autoOrient();
      const scale = Math.min(1, 1800 / Math.max(image.width, image.height));
      if (scale < 1) image.resize(Math.max(1,Math.round(image.width*scale)), Math.max(1,Math.round(image.height*scale)));
      image.strip();
      image.quality = 84;
      return image.write(MagickFormat.WebP, bytes => new Uint8Array(bytes));
    });
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new APIError(422, 'That file could not be processed. Try a smaller JPEG, PNG, or WebP image.');
  }
}

function dimensions(raw: Uint8Array, jpeg: boolean, png: boolean) {
  const view = new DataView(raw.buffer,raw.byteOffset,raw.byteLength);
  if (png) return { width:view.getUint32(16), height:view.getUint32(20) };
  if (jpeg) {
    let offset = 2;
    while (offset + 9 < raw.length) {
      if (raw[offset++] !== 255) break;
      while (raw[offset] === 255) offset++;
      const marker = raw[offset++];
      if (marker === 0xd9 || marker === 0xda) break;
      if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd8)) continue;
      const length = view.getUint16(offset);
      if (length < 2 || offset + length > raw.length) break;
      if ([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker)) return { height:view.getUint16(offset+3), width:view.getUint16(offset+5) };
      offset += length;
    }
  } else {
    let offset = 12;
    while (offset + 10 <= raw.length) {
      const chunk = new TextDecoder().decode(raw.slice(offset,offset+4));
      const size = view.getUint32(offset+4,true), start=offset+8;
      if (size < 1 || start+size>raw.length) break;
      if (chunk==='VP8X' && size>=10) return {
        width:1+raw[start+4]+(raw[start+5]<<8)+(raw[start+6]<<16),
        height:1+raw[start+7]+(raw[start+8]<<8)+(raw[start+9]<<16)
      };
      if (chunk==='VP8 ' && size>=10 && raw[start+3]===0x9d && raw[start+4]===0x01 && raw[start+5]===0x2a) return {width:view.getUint16(start+6,true)&0x3fff,height:view.getUint16(start+8,true)&0x3fff};
      if (chunk==='VP8L' && size>=5 && raw[start]===0x2f) {
        const bits=view.getUint32(start+1,true); return {width:(bits&0x3fff)+1,height:((bits>>>14)&0x3fff)+1};
      }
      offset=start+size+(size%2);
    }
  }
  throw new APIError(422,'That file has invalid image dimensions.');
}
