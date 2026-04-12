"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { calculateStats, formatCurrency } from "@/lib/price-utils";
import { Plus, Trash2, Package } from "lucide-react";
import { Empty } from "@/components/ui/empty";
import Image from "next/image";

const frequencies = [
  { value: "1m", label: "every1m" },
  { value: "15m", label: "every15m" },
  { value: "30m", label: "every30m" },
  { value: "1h", label: "every1h" },
  { value: "6h", label: "every6h" },
  { value: "12h", label: "every12h" },
  { value: "24h", label: "every24h" },
] as const;

const SCRAPER_API_MARKETPLACES = ["AE", "SA", "AU"];

export function AddTrackingView() {
  const { products, marketplaces, priceObservations, lang, addTracking, deleteProduct, getDataSource } = useStore();
  const t = translations[lang];

  const [asinInput, setAsinInput] = useState("");
  const [selectedMarketplace, setSelectedMarketplace] = useState("US");
  const [selectedFrequency, setSelectedFrequency] = useState("1h");

  const handleAddTracking = () => {
    const asins = asinInput
      .split("\n")
      .map((a) => a.trim())
      .filter(Boolean);
    if (asins.length === 0) return;

    addTracking(asins, selectedMarketplace, selectedFrequency);
    setAsinInput("");
  };

  const getProductStats = (productId: number) => {
    const observations = priceObservations.filter((o) => o.product_id === productId);
    return calculateStats(observations);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold text-foreground">{t.addTitle}</h2>
        <p className="text-sm text-muted-foreground">{t.addSub}</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Add New ASIN Card */}
        <Card className="bg-card border-border lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Plus className="h-5 w-5 text-primary" />
              {t.startTracking}
            </CardTitle>
            <CardDescription>{t.oneAsinPerLine}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-foreground">
                {t.asin}
              </label>
              <Textarea
                placeholder="B08N5WRWJ6&#10;B09G96TFF7&#10;B07ZPKN6YR"
                value={asinInput}
                onChange={(e) => setAsinInput(e.target.value)}
                className="min-h-[120px] bg-input font-mono text-sm"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-foreground">
                {t.marketplace}
              </label>
              <Select value={selectedMarketplace} onValueChange={setSelectedMarketplace}>
                <SelectTrigger className="bg-input">
                  <SelectValue placeholder={t.selectMarketplace} />
                </SelectTrigger>
                <SelectContent>
                  {marketplaces.map((mkt) => {
                    const isScraperAPI = SCRAPER_API_MARKETPLACES.includes(mkt.code);
                    return (
                      <SelectItem key={mkt.code} value={mkt.code}>
                        <span className="flex items-center gap-2">
                          <span className="font-medium">{mkt.code}</span>
                          <span className="text-muted-foreground">- {mkt.name}</span>
                          <Badge 
                            variant="outline" 
                            className={`ml-1 text-[10px] px-1.5 py-0 ${
                              isScraperAPI 
                                ? "border-cyan-500/50 text-cyan-400" 
                                : "border-amber-500/50 text-amber-400"
                            }`}
                          >
                            {isScraperAPI ? "ScraperAPI" : "Keepa"}
                          </Badge>
                        </span>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-foreground">
                {t.frequency}
              </label>
              <Select value={selectedFrequency} onValueChange={setSelectedFrequency}>
                <SelectTrigger className="bg-input">
                  <SelectValue placeholder={t.selectFrequency} />
                </SelectTrigger>
                <SelectContent>
                  {frequencies.map((freq) => (
                    <SelectItem key={freq.value} value={freq.value}>
                      {t[freq.label as keyof typeof t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleAddTracking}
              disabled={!asinInput.trim()}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="mr-2 h-4 w-4" />
              {t.startTracking}
            </Button>
          </CardContent>
        </Card>

        {/* Tracked Products List */}
        <Card className="bg-card border-border lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Package className="h-5 w-5 text-primary" />
              {t.trackedProducts}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {products.length === 0 ? (
              <Empty>
                <Empty.Icon>
                  <Package className="h-10 w-10" />
                </Empty.Icon>
                <Empty.Title>{t.noProducts}</Empty.Title>
                <Empty.Description>{t.addYourFirst}</Empty.Description>
              </Empty>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead className="text-muted-foreground">{t.asin}</TableHead>
                      <TableHead className="text-muted-foreground">{t.marketplace}</TableHead>
                      <TableHead className="text-muted-foreground">{t.dataSource}</TableHead>
                      <TableHead className="text-muted-foreground">{t.currentPrice}</TableHead>
                      <TableHead className="text-muted-foreground">{t.seller}</TableHead>
                      <TableHead className="text-muted-foreground text-right">
                        {t.action}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {products.map((product) => {
                      const stats = getProductStats(product.id);
                      const mkt = marketplaces.find((m) => m.code === product.marketplace);
                      const currency = mkt?.currency || "USD";

                      return (
                        <TableRow key={product.id} className="border-border">
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <div className="relative h-10 w-10 overflow-hidden rounded-md bg-secondary">
                                <Image
                                  src={product.image_url}
                                  alt={product.title}
                                  fill
                                  className="object-cover"
                                />
                              </div>
                              <div className="flex flex-col">
                                <span className="font-mono text-sm text-foreground">
                                  {product.asin}
                                </span>
                                <span className="text-xs text-muted-foreground truncate max-w-[180px]">
                                  {product.title}
                                </span>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="secondary"
                              className="bg-secondary text-secondary-foreground"
                            >
                              {product.marketplace}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {(() => {
                              const isScraperAPI = SCRAPER_API_MARKETPLACES.includes(product.marketplace);
                              return (
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs ${
                                    isScraperAPI 
                                      ? "border-cyan-500/50 text-cyan-400" 
                                      : "border-amber-500/50 text-amber-400"
                                  }`}
                                >
                                  {isScraperAPI ? "ScraperAPI" : "Keepa"}
                                </Badge>
                              );
                            })()}
                          </TableCell>
                          <TableCell className="font-medium text-foreground">
                            {stats ? formatCurrency(stats.lastPrice, currency) : "—"}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {product.buybox_seller || "—"}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => deleteProduct(product.id)}
                              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
