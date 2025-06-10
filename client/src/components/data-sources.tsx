import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Database, Youtube, Globe, Plus, CheckCircle, XCircle } from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { formatDistanceToNow } from "date-fns";

interface DataSourcesProps {
  agentConfigId: number;
}

export default function DataSources({ agentConfigId }: DataSourcesProps) {
  const { toast } = useToast();
  const [isAddingSource, setIsAddingSource] = useState(false);

  const { data: dataSources = [], isLoading } = useQuery({
    queryKey: ["/api/data-sources", agentConfigId],
    enabled: !!agentConfigId,
  });

  const addDataSourceMutation = useMutation({
    mutationFn: (data: any) => apiRequest('POST', '/api/data-sources', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/data-sources", agentConfigId] });
      setIsAddingSource(false);
      toast({
        title: "Success",
        description: "Data source added successfully",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to add data source",
        variant: "destructive",
      });
    }
  });

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'youtube':
        return <Youtube className="text-red-500" />;
      case 'website':
        return <Globe className="text-blue-400" />;
      default:
        return <Database className="text-purple-400" />;
    }
  };

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? (
      <CheckCircle className="w-2 h-2 text-green-400" />
    ) : (
      <XCircle className="w-2 h-2 text-red-400" />
    );
  };

  if (isLoading) {
    return (
      <Card className="glass-card rounded-2xl premium-shadow">
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-electric-blue"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-card rounded-2xl premium-shadow">
      <CardHeader>
        <CardTitle className="flex items-center text-xl font-semibold">
          <Database className="text-purple-400 mr-3" />
          Data Sources
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {dataSources.length === 0 ? (
          <div className="text-center text-gray-400 py-4">
            <Database className="mx-auto h-12 w-12 text-gray-600 mb-4" />
            <p>No data sources configured</p>
            <p className="text-sm">Add data sources to enhance your agent's knowledge</p>
          </div>
        ) : (
          dataSources.map((source: any) => (
            <div key={source.id} className="glass-card p-4 rounded-lg border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  {getSourceIcon(source.type)}
                  <span className="font-medium">{source.name}</span>
                </div>
                {getStatusIcon(source.isActive)}
              </div>
              
              {source.url && (
                <p className="text-sm text-gray-400 mb-1">{source.url}</p>
              )}
              
              {source.lastSynced && (
                <p className="text-xs text-gray-500">
                  Last synced: {formatDistanceToNow(new Date(source.lastSynced), { addSuffix: true })}
                </p>
              )}
            </div>
          ))
        )}

        {/* Add Data Source Button */}
        <Button
          onClick={() => setIsAddingSource(true)}
          disabled={addDataSourceMutation.isPending}
          variant="ghost"
          className="w-full glass-card hover:bg-white/10 transition-all duration-300 p-4 rounded-lg border border-dashed border-white/30 flex items-center justify-center space-x-2"
        >
          <Plus className="text-gray-400" />
          <span className="text-gray-400">Add Data Source</span>
        </Button>
      </CardContent>
    </Card>
  );
}
