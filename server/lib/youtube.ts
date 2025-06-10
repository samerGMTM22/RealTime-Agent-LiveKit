import { google } from 'googleapis';

const youtube = google.youtube({
  version: 'v3',
  auth: process.env.YOUTUBE_API_KEY || process.env.GOOGLE_API_KEY || 'default_key'
});

export interface ChannelInfo {
  id: string;
  title: string;
  description: string;
  subscriberCount: string;
  videoCount: string;
  viewCount: string;
  thumbnails: any;
  publishedAt: string;
  customUrl?: string;
}

export interface VideoInfo {
  id: string;
  title: string;
  description: string;
  publishedAt: string;
  viewCount: string;
  likeCount: string;
  commentCount: string;
  duration: string;
  thumbnails: any;
}

export class YouTubeService {
  async getChannelInfo(channelHandle: string): Promise<ChannelInfo | null> {
    try {
      // First try to get channel by handle/custom URL
      const searchResponse = await youtube.search.list({
        part: ['snippet'],
        q: channelHandle,
        type: ['channel'],
        maxResults: 1
      });

      if (!searchResponse.data.items || searchResponse.data.items.length === 0) {
        throw new Error(`Channel not found: ${channelHandle}`);
      }

      const channelId = searchResponse.data.items[0].snippet?.channelId;
      if (!channelId) {
        throw new Error(`Could not extract channel ID for: ${channelHandle}`);
      }

      // Get detailed channel information
      const channelResponse = await youtube.channels.list({
        part: ['snippet', 'statistics', 'brandingSettings'],
        id: [channelId]
      });

      if (!channelResponse.data.items || channelResponse.data.items.length === 0) {
        throw new Error(`Channel details not found for ID: ${channelId}`);
      }

      const channel = channelResponse.data.items[0];
      const snippet = channel.snippet;
      const statistics = channel.statistics;

      return {
        id: channelId,
        title: snippet?.title || '',
        description: snippet?.description || '',
        subscriberCount: statistics?.subscriberCount || '0',
        videoCount: statistics?.videoCount || '0',
        viewCount: statistics?.viewCount || '0',
        thumbnails: snippet?.thumbnails || {},
        publishedAt: snippet?.publishedAt || '',
        customUrl: snippet?.customUrl
      };
    } catch (error) {
      console.error('Error fetching YouTube channel info:', error);
      throw new Error(`Failed to fetch channel information: ${error.message}`);
    }
  }

  async getChannelVideos(channelId: string, maxResults: number = 10): Promise<VideoInfo[]> {
    try {
      // Get uploads playlist ID
      const channelResponse = await youtube.channels.list({
        part: ['contentDetails'],
        id: [channelId]
      });

      const uploadsPlaylistId = channelResponse.data.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;
      if (!uploadsPlaylistId) {
        throw new Error('Could not find uploads playlist');
      }

      // Get videos from uploads playlist
      const playlistResponse = await youtube.playlistItems.list({
        part: ['snippet'],
        playlistId: uploadsPlaylistId,
        maxResults
      });

      if (!playlistResponse.data.items) {
        return [];
      }

      // Get detailed video information
      const videoIds = playlistResponse.data.items
        .map(item => item.snippet?.resourceId?.videoId)
        .filter(Boolean) as string[];

      const videosResponse = await youtube.videos.list({
        part: ['snippet', 'statistics', 'contentDetails'],
        id: videoIds
      });

      if (!videosResponse.data.items) {
        return [];
      }

      return videosResponse.data.items.map(video => ({
        id: video.id || '',
        title: video.snippet?.title || '',
        description: video.snippet?.description || '',
        publishedAt: video.snippet?.publishedAt || '',
        viewCount: video.statistics?.viewCount || '0',
        likeCount: video.statistics?.likeCount || '0',
        commentCount: video.statistics?.commentCount || '0',
        duration: video.contentDetails?.duration || '',
        thumbnails: video.snippet?.thumbnails || {}
      }));
    } catch (error) {
      console.error('Error fetching YouTube videos:', error);
      throw new Error(`Failed to fetch channel videos: ${error.message}`);
    }
  }

  async searchChannelVideos(channelId: string, query: string, maxResults: number = 5): Promise<VideoInfo[]> {
    try {
      const searchResponse = await youtube.search.list({
        part: ['snippet'],
        channelId,
        q: query,
        type: ['video'],
        maxResults,
        order: 'relevance'
      });

      if (!searchResponse.data.items || searchResponse.data.items.length === 0) {
        return [];
      }

      const videoIds = searchResponse.data.items
        .map(item => item.id?.videoId)
        .filter(Boolean) as string[];

      const videosResponse = await youtube.videos.list({
        part: ['snippet', 'statistics', 'contentDetails'],
        id: videoIds
      });

      if (!videosResponse.data.items) {
        return [];
      }

      return videosResponse.data.items.map(video => ({
        id: video.id || '',
        title: video.snippet?.title || '',
        description: video.snippet?.description || '',
        publishedAt: video.snippet?.publishedAt || '',
        viewCount: video.statistics?.viewCount || '0',
        likeCount: video.statistics?.likeCount || '0',
        commentCount: video.statistics?.commentCount || '0',
        duration: video.contentDetails?.duration || '',
        thumbnails: video.snippet?.thumbnails || {}
      }));
    } catch (error) {
      console.error('Error searching YouTube videos:', error);
      throw new Error(`Failed to search channel videos: ${error.message}`);
    }
  }

  async getChannelStats(channelHandle: string): Promise<any> {
    try {
      const channelInfo = await this.getChannelInfo(channelHandle);
      if (!channelInfo) {
        throw new Error('Channel not found');
      }

      const recentVideos = await this.getChannelVideos(channelInfo.id, 5);
      
      return {
        channel: channelInfo,
        recentVideos,
        lastUpdated: new Date().toISOString()
      };
    } catch (error) {
      console.error('Error fetching YouTube channel stats:', error);
      throw new Error(`Failed to fetch channel stats: ${error.message}`);
    }
  }
}

export const youtubeService = new YouTubeService();
