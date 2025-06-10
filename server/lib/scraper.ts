import fetch from 'node-fetch';
import * as cheerio from 'cheerio';

export interface ScrapedContent {
  title: string;
  description: string;
  content: string;
  links: string[];
  images: string[];
  lastScraped: string;
}

export interface WebsiteData {
  url: string;
  pages: ScrapedContent[];
  sitemap?: string[];
  metadata: {
    domain: string;
    scrapedAt: string;
    totalPages: number;
  };
}

export class WebScraperService {
  private readonly userAgent = 'Mozilla/5.0 (compatible; VoiceAgent/1.0; +https://voiceagent.pro)';
  private readonly timeout = 10000; // 10 seconds

  async scrapeWebsite(url: string, maxDepth: number = 2): Promise<WebsiteData> {
    try {
      const domain = new URL(url).hostname;
      const visitedUrls = new Set<string>();
      const scrapedPages: ScrapedContent[] = [];
      const urlsToVisit = [url];

      for (let depth = 0; depth < maxDepth && urlsToVisit.length > 0; depth++) {
        const currentUrls = [...urlsToVisit];
        urlsToVisit.length = 0;

        for (const currentUrl of currentUrls) {
          if (visitedUrls.has(currentUrl)) continue;
          
          try {
            const pageContent = await this.scrapePage(currentUrl);
            scrapedPages.push(pageContent);
            visitedUrls.add(currentUrl);

            // Extract links for next depth level
            if (depth < maxDepth - 1) {
              const internalLinks = pageContent.links
                .filter(link => this.isInternalLink(link, domain))
                .filter(link => !visitedUrls.has(link))
                .slice(0, 5); // Limit to 5 links per page

              urlsToVisit.push(...internalLinks);
            }
          } catch (error) {
            console.warn(`Failed to scrape page ${currentUrl}:`, error.message);
          }
        }
      }

      return {
        url,
        pages: scrapedPages,
        metadata: {
          domain,
          scrapedAt: new Date().toISOString(),
          totalPages: scrapedPages.length
        }
      };
    } catch (error) {
      console.error('Error scraping website:', error);
      throw new Error(`Failed to scrape website: ${error.message}`);
    }
  }

  async scrapePage(url: string): Promise<ScrapedContent> {
    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': this.userAgent,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
          'Accept-Encoding': 'gzip, deflate',
          'Connection': 'keep-alive'
        },
        timeout: this.timeout
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const html = await response.text();
      const $ = cheerio.load(html);

      // Remove script and style elements
      $('script, style, nav, footer, .ads, .advertisement').remove();

      // Extract title
      const title = $('title').text().trim() || 
                   $('h1').first().text().trim() || 
                   'Untitled Page';

      // Extract description
      const description = $('meta[name="description"]').attr('content') || 
                         $('meta[property="og:description"]').attr('content') || 
                         $('p').first().text().substring(0, 160) || '';

      // Extract main content
      const contentSelectors = [
        'main', 'article', '.content', '.main-content', 
        '#content', '#main', '.post-content', '.entry-content'
      ];
      
      let content = '';
      for (const selector of contentSelectors) {
        const element = $(selector);
        if (element.length > 0) {
          content = element.text().trim();
          break;
        }
      }

      // Fallback to body content if no main content found
      if (!content) {
        content = $('body').text().trim();
      }

      // Clean up content
      content = content
        .replace(/\s+/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
        .substring(0, 5000); // Limit content length

      // Extract links
      const links: string[] = [];
      $('a[href]').each((_, element) => {
        const href = $(element).attr('href');
        if (href) {
          try {
            const absoluteUrl = new URL(href, url).href;
            links.push(absoluteUrl);
          } catch (e) {
            // Invalid URL, skip
          }
        }
      });

      // Extract images
      const images: string[] = [];
      $('img[src]').each((_, element) => {
        const src = $(element).attr('src');
        if (src) {
          try {
            const absoluteUrl = new URL(src, url).href;
            images.push(absoluteUrl);
          } catch (e) {
            // Invalid URL, skip
          }
        }
      });

      return {
        title,
        description,
        content,
        links: [...new Set(links)], // Remove duplicates
        images: [...new Set(images)], // Remove duplicates
        lastScraped: new Date().toISOString()
      };
    } catch (error) {
      console.error(`Error scraping page ${url}:`, error);
      throw new Error(`Failed to scrape page: ${error.message}`);
    }
  }

  private isInternalLink(link: string, domain: string): boolean {
    try {
      const linkUrl = new URL(link);
      return linkUrl.hostname === domain;
    } catch (error) {
      return false;
    }
  }

  async getWebsiteContent(url: string): Promise<string> {
    try {
      const websiteData = await this.scrapeWebsite(url, 2);
      
      // Combine all page content into a searchable format
      const combinedContent = websiteData.pages
        .map(page => `${page.title}\n${page.description}\n${page.content}`)
        .join('\n\n---\n\n');

      return combinedContent;
    } catch (error) {
      console.error('Error getting website content:', error);
      throw new Error(`Failed to get website content: ${error.message}`);
    }
  }
}

export const webScraperService = new WebScraperService();
