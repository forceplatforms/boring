"use client";

import { useState } from "react";
import { SearchIcon, AlertCircle, Sparkles, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SearchInterface } from "@/components/search/search-interface";
import { SearchResults } from "@/components/search/search-results";
import { useSearchDocuments } from "@/lib/hooks/use-search";
import type { QueryRequest, QueryResponse } from "@/lib/types/api";

export default function SearchPage() {
  const [searchResults, setSearchResults] = useState<QueryResponse | null>(
    null
  );
  const searchMutation = useSearchDocuments();

  const handleSearch = async (params: QueryRequest) => {
    try {
      const results = await searchMutation.mutateAsync(params);
      setSearchResults(results);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent rounded-2xl blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-4 mb-3">
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/25">
              <SearchIcon className="h-7 w-7 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
                Document Search
              </h1>
              <p className="text-muted-foreground mt-1">
                AI-powered semantic search with ColPali embeddings
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Info Card */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
        <CardContent className="flex items-start gap-4 py-5">
          <div className="p-2 rounded-lg bg-primary/10 shrink-0">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 space-y-2">
            <p className="text-sm font-medium text-foreground">
              Semantic Search Technology
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Use natural language queries to find relevant pages. Our AI understands context and meaning, not just keywords—making it easy to discover insights across your document library.
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-background/50 border border-border">
                <Sparkles className="h-3 w-3 text-primary" />
                <span className="text-xs font-medium">Context-aware</span>
              </div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-background/50 border border-border">
                <Sparkles className="h-3 w-3 text-primary" />
                <span className="text-xs font-medium">Multi-lingual</span>
              </div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-background/50 border border-border">
                <Sparkles className="h-3 w-3 text-primary" />
                <span className="text-xs font-medium">Visual understanding</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search Interface */}
      <Card className="border-2">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <SearchIcon className="h-5 w-5 text-primary" />
            Search Parameters
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <SearchInterface
            onSearch={handleSearch}
            isSearching={searchMutation.isPending}
          />
        </CardContent>
      </Card>

      {/* Error State */}
      {searchMutation.isError && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-start gap-4 py-5">
            <div className="p-2 rounded-lg bg-destructive/10 shrink-0">
              <AlertCircle className="h-5 w-5 text-destructive" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive mb-1">
                Search failed
              </p>
              <p className="text-sm text-muted-foreground">
                {searchMutation.error instanceof Error
                  ? searchMutation.error.message
                  : "An unexpected error occurred. Please try again."}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search Results */}
      {searchResults && <SearchResults results={searchResults} />}

      {/* Empty State - Before First Search */}
      {!searchResults && !searchMutation.isPending && !searchMutation.isError && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-20 text-center">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-primary/10 rounded-full blur-2xl" />
              <div className="relative flex h-28 w-28 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 backdrop-blur-sm">
                <SearchIcon className="h-14 w-14 text-primary" />
              </div>
            </div>
            <h3 className="text-2xl font-semibold mb-2">
              Ready to search
            </h3>
            <p className="text-sm text-muted-foreground max-w-md mb-6">
              Enter a search query above to find relevant pages in your indexed documents using AI-powered semantic search
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              <button
                onClick={() => {
                  const input = document.querySelector('input[type="text"]') as HTMLInputElement;
                  if (input) {
                    input.value = "What are the key financial metrics?";
                    input.focus();
                  }
                }}
                className="text-xs px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 transition-colors"
              >
                Try: "What are the key financial metrics?"
              </button>
              <button
                onClick={() => {
                  const input = document.querySelector('input[type="text"]') as HTMLInputElement;
                  if (input) {
                    input.value = "manufacturing quality control";
                    input.focus();
                  }
                }}
                className="text-xs px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 transition-colors"
              >
                Try: "manufacturing quality control"
              </button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
