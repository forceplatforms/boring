"use client";

import { FileText, Image as ImageIcon, ExternalLink, Trophy, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { QueryResponse } from "@/lib/types/api";

interface SearchResultsProps {
  results: QueryResponse | null;
}

function getScoreColor(score: number) {
  if (score >= 0.8) return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
  if (score >= 0.6) return "text-blue-500 bg-blue-500/10 border-blue-500/20";
  if (score >= 0.4) return "text-amber-500 bg-amber-500/10 border-amber-500/20";
  return "text-slate-500 bg-slate-500/10 border-slate-500/20";
}

function getRankBadge(rank: number) {
  if (rank === 1) return { icon: Trophy, className: "text-amber-400 bg-amber-400/10" };
  if (rank === 2) return { icon: Trophy, className: "text-slate-300 bg-slate-300/10" };
  if (rank === 3) return { icon: Trophy, className: "text-orange-400 bg-orange-400/10" };
  return { icon: Sparkles, className: "text-primary bg-primary/10" };
}

export function SearchResults({ results }: SearchResultsProps) {
  if (!results) {
    return null;
  }

  if (results.results_count === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-20 text-center">
          <div className="relative mb-6">
            <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 backdrop-blur-sm">
              <FileText className="h-12 w-12 text-primary" />
            </div>
            <div className="absolute -right-1 -top-1 h-6 w-6 rounded-full bg-background border-2 border-border flex items-center justify-center">
              <span className="text-xs">0</span>
            </div>
          </div>
          <h3 className="text-xl font-semibold mb-2">No results found</h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Try adjusting your search query or lowering the similarity threshold to see more results
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Results Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-2xl font-bold">
              {results.results_count} Result{results.results_count !== 1 ? "s" : ""}
            </h3>
            <Badge variant="outline" className="font-normal">
              from {results.total_documents_in_index} docs
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Searching in{" "}
            <span className="font-medium text-foreground">
              {results.index_name}
            </span>{" "}
            collection
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Query:</span>
          <Badge variant="secondary" className="font-normal max-w-[300px] truncate">
            {results.query}
          </Badge>
        </div>
      </div>

      {/* Results Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {results.results.map((result, index) => {
          const rankBadge = getRankBadge(result.rank);
          const RankIcon = rankBadge.icon;

          return (
            <Card
              key={`${result.document_id}-${result.page_number}-${result.rank}`}
              className="group relative overflow-hidden hover:shadow-xl hover:border-primary/50 transition-all duration-300 animate-in fade-in-0 zoom-in-95"
              style={{
                animationDelay: `${index * 50}ms`,
                animationFillMode: "backwards"
              }}
            >
              <CardContent className="p-0">
                {/* Page Image Container */}
                <div className="relative aspect-[3/4] overflow-hidden bg-gradient-to-br from-muted/50 to-muted">
                  {result.page_image_url ? (
                    <>
                      <img
                        src={result.page_image_url}
                        alt={`Page ${result.page_number} of ${result.filename}`}
                        className="w-full h-full object-contain transition-transform duration-500 group-hover:scale-105"
                        loading="lazy"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-background/0 to-background/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    </>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <ImageIcon className="h-16 w-16 text-muted-foreground/30" />
                    </div>
                  )}

                  {/* Rank Badge */}
                  <div className="absolute top-3 left-3">
                    <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg backdrop-blur-sm border ${rankBadge.className}`}>
                      <RankIcon className="h-3.5 w-3.5" />
                      <span className="text-xs font-bold">#{result.rank}</span>
                    </div>
                  </div>

                  {/* Score Badge */}
                  <div className="absolute top-3 right-3">
                    <div className={`px-3 py-1.5 rounded-lg backdrop-blur-sm border ${getScoreColor(result.score)}`}>
                      <span className="text-xs font-bold">
                        {(result.score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Page Number */}
                  <div className="absolute bottom-3 right-3">
                    <Badge variant="secondary" className="backdrop-blur-sm bg-background/90 border shadow-lg">
                      Page {result.page_number}
                    </Badge>
                  </div>
                </div>

                {/* Document Info */}
                <div className="p-4 space-y-3">
                  <div className="flex items-start gap-2.5">
                    <div className="p-2 rounded-lg bg-primary/10 shrink-0">
                      <FileText className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p
                        className="text-sm font-medium line-clamp-1 group-hover:text-primary transition-colors"
                        title={result.filename}
                      >
                        {result.filename}
                      </p>
                      {(result.doc_type || result.doc_category) && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {result.doc_type}
                          {result.doc_category && result.doc_type && " • "}
                          {result.doc_category}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Metadata */}
                  {Object.keys(result.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(result.metadata)
                        .slice(0, 2)
                        .map(([key, value]) => (
                          <Badge
                            key={key}
                            variant="outline"
                            className="text-xs font-normal bg-background/50"
                          >
                            <span className="text-muted-foreground">{key}:</span>
                            <span className="ml-1">
                              {String(value).substring(0, 15)}
                              {String(value).length > 15 ? "..." : ""}
                            </span>
                          </Badge>
                        ))}
                    </div>
                  )}

                  {/* View Link */}
                  {result.document_id && (
                    <a
                      href={`/documents/${result.document_id}`}
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors group/link"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <span>View document</span>
                      <ExternalLink className="h-3.5 w-3.5 transition-transform group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5" />
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
