/** Extract the first tournament link from mobile share text, omitting tracking data. */
export function extractTopDeckTournamentUrl(input: string): string | null {
  const links = input.matchAll(
    /(?:^|[\s(<\[{'"“‘:])((?:https?:\/\/)?(?:www\.)?topdeck\.gg\/[^\s<>"'“”‘’]+)/gi,
  );
  for (const match of links) {
    const candidate = match[1].replace(/[.,!?:;)\]}]+$/, "");
    try {
      const url = new URL(/^https?:\/\//i.test(candidate) ? candidate : `https://${candidate}`);
      const path = url.pathname.match(/^\/(event|bracket|tournament|tournaments)\/([a-z0-9_-]+)(?:\/|$)/i);
      if (path) return `https://topdeck.gg/${path[1].toLowerCase()}/${path[2]}`;
    } catch {
      // Continue past malformed links to a later tournament link in the message.
    }
  }
  return null;
}
