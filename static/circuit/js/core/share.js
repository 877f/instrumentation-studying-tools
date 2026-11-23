/* Pack a circuit into a URL hash and back. Compressed with deflate when the browser can,
   then base64url. "z…" is compressed, "j…" is plain JSON. */

const b64url = (bytes) => {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};
const unb64url = (s) => {
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
};

export async function encodeShare(obj) {
  const bytes = new TextEncoder().encode(JSON.stringify(obj));
  if (typeof CompressionStream === 'function') {
    const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate-raw'));
    return `z${b64url(new Uint8Array(await new Response(stream).arrayBuffer()))}`;
  }
  return `j${b64url(bytes)}`;
}

/** Returns the decoded object, or null if the text isn't a valid share code. */
export async function decodeShare(code) {
  try {
    if (code[0] === 'j') return JSON.parse(new TextDecoder().decode(unb64url(code.slice(1))));
    if (code[0] === 'z' && typeof DecompressionStream === 'function') {
      const stream = new Blob([unb64url(code.slice(1))]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
      return JSON.parse(await new Response(stream).text());
    }
  } catch { /* fall through */ }
  return null;
}
