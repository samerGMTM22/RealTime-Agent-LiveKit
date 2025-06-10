import { DataSource } from "@shared/schema";
import { youtubeService } from "../lib/youtube";
import { webScraperService } from "../lib/scraper";
import { openaiService } from "../lib/openai";

export interface DataSourceConnector {
  type: string;
  name: string;
  description: string;
  configFields: Array<{
    key: string;
    label: string;
    type: 'text' | 'url' | 'select' | 'number' | 'boolean';
    required: boolean;
    options?: string[];
    placeholder?: string;
  }>;
  testConnection: (config: Record<string, any>) => Promise<boolean>;
  fetchData: (config: Record<string, any>) => Promise<any>;
  processData: (rawData: any) => Promise<string>;
}

export const DATA_SOURCE_CONNECTORS: Record<string, DataSourceConnector> = {
  youtube: {
    type: 'youtube',
    name: 'YouTube Channel',
    description: 'Connect to a YouTube channel to access video information, statistics, and content',
    configFields: [
      {
        key: 'channelHandle',
        label: 'Channel Handle (e.g., @YourChannel)',
        type: 'text',
        required: true,
        placeholder: '@GiveMeTheMic22'
      },
      {
        key: 'includeVideos',
        label: 'Include Recent Videos',
        type: 'boolean',
        required: false
      },
      {
        key: 'maxVideos',
        label: 'Max Videos to Fetch',
        type: 'number',
        required: false,
        placeholder: '10'
      }
    ],
    testConnection: async (config) => {
      try {
        const channelInfo = await youtubeService.getChannelInfo(config.channelHandle);
        return !!channelInfo;
      } catch (error) {
        console.error('YouTube connection test failed:', error);
        return false;
      }
    },
    fetchData: async (config) => {
      const channelInfo = await youtubeService.getChannelInfo(config.channelHandle);
      if (!channelInfo) throw new Error('Channel not found');
      
      let videos = [];
      if (config.includeVideos) {
        videos = await youtubeService.getChannelVideos(channelInfo.id, config.maxVideos || 10);
      }
      
      return { channel: channelInfo, videos };
    },
    processData: async (rawData) => {
      const { channel, videos } = rawData;
      
      let content = `Channel: ${channel.title}\n`;
      content += `Description: ${channel.description}\n`;
      content += `Subscribers: ${channel.subscriberCount}\n`;
      content += `Total Videos: ${channel.videoCount}\n`;
      content += `Total Views: ${channel.viewCount}\n\n`;
      
      if (videos && videos.length > 0) {
        content += 'Recent Videos:\n';
        videos.forEach((video: any) => {
          content += `- ${video.title}\n`;
          content += `  Views: ${video.viewCount} | Likes: ${video.likeCount}\n`;
          content += `  Description: ${video.description.substring(0, 200)}...\n\n`;
        });
      }
      
      return content;
    }
  },

  website: {
    type: 'website',
    name: 'Website Scraper',
    description: 'Scrape and index content from any website for agent knowledge',
    configFields: [
      {
        key: 'url',
        label: 'Website URL',
        type: 'url',
        required: true,
        placeholder: 'https://example.com'
      },
      {
        key: 'crawlDepth',
        label: 'Crawl Depth',
        type: 'select',
        required: false,
        options: ['1', '2', '3', '4', '5']
      },
      {
        key: 'includeImages',
        label: 'Include Image Descriptions',
        type: 'boolean',
        required: false
      }
    ],
    testConnection: async (config) => {
      try {
        const response = await fetch(config.url, { method: 'HEAD' });
        return response.ok;
      } catch (error) {
        console.error('Website connection test failed:', error);
        return false;
      }
    },
    fetchData: async (config) => {
      return await webScraperService.scrapeWebsite(config.url, parseInt(config.crawlDepth) || 2);
    },
    processData: async (rawData) => {
      const { pages, metadata } = rawData;
      
      let content = `Website: ${metadata.domain}\n`;
      content += `Scraped: ${metadata.scrapedAt}\n`;
      content += `Total Pages: ${metadata.totalPages}\n\n`;
      
      pages.forEach((page: any) => {
        content += `Page: ${page.title}\n`;
        content += `Description: ${page.description}\n`;
        content += `Content: ${page.content.substring(0, 1000)}...\n\n`;
      });
      
      return content;
    }
  },

  document: {
    type: 'document',
    name: 'Document Upload',
    description: 'Upload and process text documents, PDFs, or other files',
    configFields: [
      {
        key: 'fileName',
        label: 'File Name',
        type: 'text',
        required: true,
        placeholder: 'document.pdf'
      },
      {
        key: 'fileContent',
        label: 'File Content (text)',
        type: 'text',
        required: true,
        placeholder: 'Paste your document content here...'
      }
    ],
    testConnection: async (config) => {
      return !!(config.fileName && config.fileContent);
    },
    fetchData: async (config) => {
      return {
        fileName: config.fileName,
        content: config.fileContent,
        processedAt: new Date().toISOString()
      };
    },
    processData: async (rawData) => {
      return `Document: ${rawData.fileName}\nProcessed: ${rawData.processedAt}\n\nContent:\n${rawData.content}`;
    }
  },

  api: {
    type: 'api',
    name: 'Custom API',
    description: 'Connect to any REST API endpoint for dynamic data retrieval',
    configFields: [
      {
        key: 'endpoint',
        label: 'API Endpoint URL',
        type: 'url',
        required: true,
        placeholder: 'https://api.example.com/data'
      },
      {
        key: 'method',
        label: 'HTTP Method',
        type: 'select',
        required: true,
        options: ['GET', 'POST']
      },
      {
        key: 'headers',
        label: 'Headers (JSON format)',
        type: 'text',
        required: false,
        placeholder: '{"Authorization": "Bearer token"}'
      },
      {
        key: 'dataPath',
        label: 'Data Path (dot notation)',
        type: 'text',
        required: false,
        placeholder: 'data.results'
      }
    ],
    testConnection: async (config) => {
      try {
        const headers = config.headers ? JSON.parse(config.headers) : {};
        const response = await fetch(config.endpoint, {
          method: config.method || 'GET',
          headers: { 'Content-Type': 'application/json', ...headers }
        });
        return response.ok;
      } catch (error) {
        console.error('API connection test failed:', error);
        return false;
      }
    },
    fetchData: async (config) => {
      const headers = config.headers ? JSON.parse(config.headers) : {};
      const response = await fetch(config.endpoint, {
        method: config.method || 'GET',
        headers: { 'Content-Type': 'application/json', ...headers }
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Extract data using path if provided
      if (config.dataPath) {
        const pathParts = config.dataPath.split('.');
        let extractedData = data;
        for (const part of pathParts) {
          extractedData = extractedData[part];
          if (extractedData === undefined) break;
        }
        return extractedData || data;
      }
      
      return data;
    },
    processData: async (rawData) => {
      return `API Data Retrieved:\n${JSON.stringify(rawData, null, 2)}`;
    }
  },

  rss: {
    type: 'rss',
    name: 'RSS Feed',
    description: 'Monitor RSS feeds for latest updates and news',
    configFields: [
      {
        key: 'feedUrl',
        label: 'RSS Feed URL',
        type: 'url',
        required: true,
        placeholder: 'https://example.com/feed.xml'
      },
      {
        key: 'maxItems',
        label: 'Max Items to Fetch',
        type: 'number',
        required: false,
        placeholder: '10'
      }
    ],
    testConnection: async (config) => {
      try {
        const response = await fetch(config.feedUrl);
        return response.ok && response.headers.get('content-type')?.includes('xml');
      } catch (error) {
        console.error('RSS feed connection test failed:', error);
        return false;
      }
    },
    fetchData: async (config) => {
      // For now, return mock data structure - would need RSS parser in production
      return {
        feedUrl: config.feedUrl,
        items: [],
        fetchedAt: new Date().toISOString()
      };
    },
    processData: async (rawData) => {
      return `RSS Feed: ${rawData.feedUrl}\nFetched: ${rawData.fetchedAt}\nItems: ${rawData.items.length}`;
    }
  }
};

export class DataSourceManager {
  async testDataSource(type: string, config: Record<string, any>): Promise<boolean> {
    const connector = DATA_SOURCE_CONNECTORS[type];
    if (!connector) throw new Error(`Unknown data source type: ${type}`);
    
    return await connector.testConnection(config);
  }

  async syncDataSource(dataSource: DataSource): Promise<string> {
    const connector = DATA_SOURCE_CONNECTORS[dataSource.type];
    if (!connector) throw new Error(`Unknown data source type: ${dataSource.type}`);
    
    try {
      const rawData = await connector.fetchData(dataSource.metadata || {});
      const processedContent = await connector.processData(rawData);
      
      return processedContent;
    } catch (error) {
      console.error(`Failed to sync data source ${dataSource.name}:`, error);
      throw error;
    }
  }

  async getAllConnectorTypes(): Promise<DataSourceConnector[]> {
    return Object.values(DATA_SOURCE_CONNECTORS);
  }

  getConnector(type: string): DataSourceConnector | undefined {
    return DATA_SOURCE_CONNECTORS[type];
  }
}

export const dataSourceManager = new DataSourceManager();