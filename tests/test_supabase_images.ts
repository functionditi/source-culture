import { ImageMagick, MagickColors, MagickFormat } from 'npm:@imagemagick/magick-wasm@0.0.45';
import { cleanImage } from '../supabase/functions/source-culture/images.ts';

const png='iVBORw0KGgoAAAANSUhEUgAAAAYAAAADCAIAAAA/Y+msAAAAEklEQVR4nGP8z4AOmDBEsAkBADisAQVnEAmgAAAAAElFTkSuQmCC';
// Six by three pixels, EXIF orientation 6, with a private metadata marker.
const jpeg='/9j/4AAQSkZJRgABAQAAAQABAAD/4QA+RXhpZgAATU0AKgAAAAgAAgESAAMAAAABAAYAAJKGAAEAAAAQAAAAJgAAAABwcml2YXRlR1BTbWFya2Vy/9sAQwAIBgYHBgUIBwcHCQkICgwUDQwLCwwZEhMPFB0aHx4dGhwcICQuJyAiLCMcHCg3KSwwMTQ0NB8nOT04MjwuMzQy/9sAQwEJCQkMCwwYDQ0YMiEcITIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy/8AAEQgAAwAGAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/aAAwDAQACEQMRAD8A4uiiivmT9xP/2Q==';
function assert(value:unknown,message='Assertion failed'){if(!value)throw new Error(message);}
async function rejects(value:string,pattern:RegExp){try{await cleanImage(value);}catch(error){assert(pattern.test(String(error)));return;}throw new Error('Expected image rejection.');}
Deno.test('images are re-encoded to WebP with orientation applied and private metadata stripped',async()=>{
  const output=await cleanImage(jpeg);
  const text=new TextDecoder().decode(output);
  assert(text.startsWith('RIFF')&&text.slice(8,12)==='WEBP');
  assert(!text.includes('privateGPSmarker')&&!text.includes('EXIF'));
  ImageMagick.read(output,image=>{assert(image.width===3&&image.height===6,'EXIF rotation must be applied');});
  const again=await cleanImage(btoa(String.fromCharCode(...output)));
  assert(again.length>0,'Clean WebP should be accepted as input');
});
Deno.test('PNG is decoded and encoded on the server',async()=>{
  const output=await cleanImage(png);
  ImageMagick.read(output,image=>{assert(image.width===6&&image.height===3);});
});
Deno.test('photographs are resized to 1800 pixels while preserving proportions',async()=>{
  await cleanImage(png);
  const input=ImageMagick.read(MagickColors.Red,2400,1600,image=>image.write(MagickFormat.Jpeg,bytes=>new Uint8Array(bytes)));
  const output=await cleanImage(btoa(String.fromCharCode(...input)));
  ImageMagick.read(output,image=>{assert(image.width===1800&&image.height===1200);});
});
Deno.test('unsupported files and compressed image bombs are rejected before full decoding',async()=>{
  await rejects(btoa('<svg onload="alert(1)"></svg>'),/JPEG, PNG, or WebP/);
  await rejects('not base64',/valid image/);
  const bomb=Uint8Array.from(atob(png),c=>c.charCodeAt(0));
  new DataView(bomb.buffer).setUint32(16,10000000);
  await rejects(btoa(String.fromCharCode(...bomb)),/24 megapixels/);
});
