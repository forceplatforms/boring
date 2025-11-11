"use client";

import { useState } from "react";
import { Search, Settings2, ChevronDown, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { QueryRequest } from "@/lib/types/api";

interface SearchInterfaceProps {
  onSearch: (params: QueryRequest) => void;
  isSearching?: boolean;
}

export function SearchInterface({
  onSearch,
  isSearching = false,
}: SearchInterfaceProps) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.0);
  const [indexName, setIndexName] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const request: QueryRequest = {
      query: query.trim(),
      k: topK,
      min_threshold: threshold,
    };

    if (indexName.trim()) {
      request.index_name = indexName.trim();
    }

    onSearch(request);
  };

  return (
    <form onSubmit={handleSearch} className="space-y-6">
      {/* Main Search Input */}
      <div className="space-y-3">
        <Label htmlFor="query" className="text-base font-medium">
          Search Query
        </Label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <Search className="h-5 w-5 text-muted-foreground" />
              <div className="h-5 w-px bg-border" />
            </div>
            <Input
              id="query"
              type="text"
              placeholder="Ask anything... e.g., What are the payment terms?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-14 pl-14 pr-4 text-base bg-background border-2 border-border hover:border-primary/50 focus:border-primary transition-all duration-200"
              disabled={isSearching}
            />
            {query && !isSearching && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
          <Button
            type="submit"
            disabled={!query.trim() || isSearching}
            size="lg"
            className="h-14 px-8 gap-2 font-medium shadow-lg hover:shadow-xl transition-all duration-200"
          >
            {isSearching ? (
              <>
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Searching
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5" />
                Search
              </>
            )}
          </Button>
        </div>
        <p className="text-sm text-muted-foreground pl-1">
          Powered by AI semantic search for natural language understanding
        </p>
      </div>

      {/* Advanced Parameters */}
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-border hover:border-primary/50 hover:bg-accent/50 transition-all duration-200 group"
        >
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-md bg-primary/10 group-hover:bg-primary/20 transition-colors">
              <Settings2 className="h-4 w-4 text-primary" />
            </div>
            <span className="font-medium text-sm">
              Advanced Parameters
            </span>
          </div>
          <ChevronDown
            className={`h-5 w-5 text-muted-foreground transition-transform duration-300 ${
              showAdvanced ? "rotate-180" : ""
            }`}
          />
        </button>

        {showAdvanced && (
          <div className="space-y-6 animate-in slide-in-from-top-2 duration-300">
            <div className="grid gap-6 md:grid-cols-3">
              {/* Top-K Parameter */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="topK" className="text-sm font-medium">
                    Results Count
                  </Label>
                  <span className="text-sm font-semibold text-primary tabular-nums">
                    {topK}
                  </span>
                </div>
                <div className="space-y-2">
                  <input
                    id="topK"
                    type="range"
                    min={1}
                    max={50}
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value))}
                    disabled={isSearching}
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>1</span>
                    <span>50</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Number of top results to return
                </p>
              </div>

              {/* Threshold Parameter */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="threshold" className="text-sm font-medium">
                    Min Similarity
                  </Label>
                  <span className="text-sm font-semibold text-primary tabular-nums">
                    {(threshold * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="space-y-2">
                  <input
                    id="threshold"
                    type="range"
                    min={0}
                    max={100}
                    value={threshold * 100}
                    onChange={(e) =>
                      setThreshold(parseInt(e.target.value) / 100)
                    }
                    disabled={isSearching}
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>0%</span>
                    <span>100%</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Filter results below this score
                </p>
              </div>

              {/* Index Name Parameter */}
              <div className="space-y-3">
                <Label htmlFor="indexName" className="text-sm font-medium">
                  Collection Name
                </Label>
                <Input
                  id="indexName"
                  type="text"
                  placeholder="Auto-detect"
                  value={indexName}
                  onChange={(e) => setIndexName(e.target.value)}
                  disabled={isSearching}
                  className="h-10 bg-background border-2 border-border hover:border-primary/50 focus:border-primary transition-all"
                />
                <p className="text-xs text-muted-foreground">
                  Milvus collection to search
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </form>
  );
}
