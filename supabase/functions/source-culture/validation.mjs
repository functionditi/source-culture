// Shared by the Edge Function and Node's behavioral tests. Never trust form HTML
// or client-supplied identity, consent, filenames, roles, or image MIME types.
export const ACTIVITIES = ['food and cooking', 'craft and making', 'games and play', 'remembering and recording', 'exchange and sharing', 'navigation and place', 'everyday coordination'];
export const SOURCE_TYPES = ['academic article', 'book or chapter', 'thesis or dissertation', 'video', 'blog or essay', 'project documentation', 'podcast or audio', 'interview or oral account', 'archive or exhibition', 'other'];
export const RELATIONSHIPS = ['documents this practice', 'supports this specific claim', 'informs this interpretation', 'offers a related example', 'further reading or viewing'];
export class APIError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
export function object(value, message = 'Expected a request object.') {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new APIError(422, message);
  return value;
}
function field(record, name, limit = 12000, required = false) {
  const value = record[name] ?? '';
  if (typeof value !== 'string' || value.length > limit) throw new APIError(422, `${name.replaceAll('_', ' ')} is too long or has an invalid format.`);
  if (required && !value.trim()) throw new APIError(422, `Please complete ${name.replaceAll('_', ' ')}.`);
  return value.trim();
}
export function email(value) {
  if (typeof value !== 'string' || value.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) throw new APIError(422, 'Enter a valid private email address.');
  return value.trim().toLowerCase();
}
export function validateSource(value) {
  const source = object(value, 'Check the source details.');
  const keys = ['source_id', 'type', 'title', 'creators', 'date', 'language', 'url', 'access_date', 'annotation', 'doi', 'venue', 'volume', 'pages', 'publisher', 'edition', 'chapter', 'isbn', 'platform', 'duration', 'locator', 'interviewer', 'recording', 'translation', 'custom_type', 'relation', 'block_id'];
  const result = Object.fromEntries(keys.map(key => [key, field(source, key, 4000)]));
  if (!SOURCE_TYPES.includes(result.type) || !result.title) throw new APIError(422, 'Every source needs a type and a title or descriptive label.');
  if (result.url) {
    let url;
    try { url = new URL(result.url); } catch { throw new APIError(422, 'Source links must be ordinary HTTP or HTTPS URLs.'); }
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) throw new APIError(422, 'Source links must be ordinary HTTP or HTTPS URLs.');
  }
  if (result.type === 'interview or oral account' && source.oral_permission !== true) throw new APIError(422, 'Confirm permission to share this oral account.');
  result.oral_permission = source.oral_permission === true;
  result.relation ||= 'further reading or viewing';
  if (!RELATIONSHIPS.includes(result.relation) || !['', 'story', 'account', 'judgement'].includes(result.block_id)) throw new APIError(422, 'Choose a valid source relationship and passage.');
  return result;
}
export function canonicalURL(value) {
  if (!value) return '';
  const url = new URL(value);
  for (const key of [...url.searchParams.keys()]) if (key.startsWith('utm_')) url.searchParams.delete(key);
  url.hash = '';
  url.pathname = url.pathname.replace(/\/$/, '');
  return url.toString().replace(/\/$/, '');
}
export function validateSubmission(value) {
  const payload = object(value);
  const kind = payload.kind || 'practice';
  if (!['practice', 'variation', 'source', 'correction'].includes(kind)) throw new APIError(422, 'Choose a contribution type.');
  const keys = ['title', 'summary', 'original_name', 'language', 'context', 'place', 'community', 'relationship', 'account', 'materials', 'steps', 'judgement', 'similar', 'changes', 'prompt', 'display_name', 'reuse'];
  const content = Object.fromEntries(keys.map(key => [key, field(payload, key, key === 'title' ? 400 : 12000, key === 'title')]));
  content.display_name ||= 'anonymous contributor';
  content.reuse ||= 'credit; no additional reuse licence';
  content.entry_type = field(payload, 'entry_type', 80) || 'practice';
  if (!['project', 'practice', 'experiment'].includes(content.entry_type)) throw new APIError(422, 'Choose project, practice, or experiment.');
  const tags = payload.tags ?? [];
  if (!Array.isArray(tags) || tags.length > 12 || tags.some(tag => typeof tag !== 'string' || tag.length > 80)) throw new APIError(422, 'Use at most 12 short activity or suggested tags.');
  content.tags = tags;
  if (payload.publication_permission !== true || payload.rights_confirmation !== true) throw new APIError(422, 'Publication permission and confirmation that you may share this material are required.');
  if (['practice', 'variation'].includes(kind)) {
    for (const key of ['summary', 'relationship', 'account']) if (!content[key]) throw new APIError(422, `Please complete ${key}.`);
    if (!['personal experience', 'learned from someone', 'observation', 'source-based research'].includes(content.relationship)) throw new APIError(422, 'Choose how you know this practice.');
    if (kind === 'variation' && (!content.similar || !content.changes)) throw new APIError(422, 'Describe what is similar and what changes in your variation.');
  }
  const references = payload.references ?? [];
  if (!Array.isArray(references) || references.length > 20) throw new APIError(422, 'Use at most 20 sources.');
  content.references = references.map(validateSource);
  for (const reference of content.references) {
    const key = { story: 'context', account: 'account', judgement: 'judgement' }[reference.block_id];
    if (key && !content[key]) throw new APIError(422, 'The citation points to an empty passage.');
    reference.canonical_url = canonicalURL(reference.url);
    reference.canonical_doi = reference.doi.toLowerCase().replace(/^https:\/\/doi\.org\//, '');
  }
  if (content.relationship === 'source-based research' && !references.length) throw new APIError(422, 'A source-based account needs at least one identified source. Print and oral sources do not need a URL.');
  if (kind === 'source') {
    content.source = validateSource(payload.source);
    content.title = content.source.title;
    if (!content.source.annotation) throw new APIError(422, 'Explain why this source is relevant.');
    content.source.canonical_url = canonicalURL(content.source.url);
    content.source.canonical_doi = content.source.doi.toLowerCase().replace(/^https:\/\/doi\.org\//, '');
  }
  if (kind === 'correction' && !content.account) throw new APIError(422, 'Please describe the correction.');
  const images = payload.images ?? [], kept = payload.keep_media ?? [];
  if (!Array.isArray(images) || !Array.isArray(kept) || images.length + kept.length > 4 || kept.some(id => typeof id !== 'string')) throw new APIError(422, 'Attach or keep at most four images.');
  const cleanImages = images.map(image => {
    object(image, 'Check the image details.');
    if (image.permission !== true) throw new APIError(422, 'Images need your permission to publish them.');
    const data = field(image, 'data', 7 * 1024 * 1024, true);
    return { data, alt: field(image, 'alt', 2000, true), caption: field(image, 'caption', 2000), credit: field(image, 'credit', 400), licence: field(image, 'licence', 200) || 'no additional reuse licence' };
  });
  return { kind, content, images: cleanImages, keep_media: kept, parent_id: field(payload, 'parent_id', 100) || null, target_id: field(payload, 'target_id', 100) || null };
}
