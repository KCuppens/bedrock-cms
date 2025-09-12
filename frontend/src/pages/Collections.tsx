import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Plus, FolderOpen, Search, Filter } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";

const Collections = () => {
  const collections = [
    {
      id: 1,
      name: "Blog Articles",
      description: "Main blog content collection",
      itemCount: 45,
      lastModified: "2 hours ago",
      type: "Blog Posts"
    },
    {
      id: 2,
      name: "Product Catalog",
      description: "E-commerce product listings",
      itemCount: 128,
      lastModified: "1 day ago",
      type: "Products"
    },
    {
      id: 3,
      name: "Team Members",
      description: "Company team profiles",
      itemCount: 12,
      lastModified: "3 days ago",
      type: "People"
    }
  ];

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-1 ml-72">
        <TopNavbar />

        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Collections</h1>
              <p className="text-muted-foreground">Organize your content with structured collections</p>
            </div>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Collection
            </Button>
          </div>

          <Tabs defaultValue="all" className="space-y-4">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="all">All Collections</TabsTrigger>
                <TabsTrigger value="blog">Blog Content</TabsTrigger>
                <TabsTrigger value="products">Products</TabsTrigger>
                <TabsTrigger value="people">People</TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input placeholder="Search collections..." className="pl-10 w-64" />
                </div>
                <Button variant="outline" size="sm">
                  <Filter className="w-4 h-4 mr-2" />
                  Filter
                </Button>
              </div>
            </div>

            <TabsContent value="all" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {collections.map((collection) => (
                <Card key={collection.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                        <FolderOpen className="w-5 h-5 text-primary" />
                      </div>
                      <div className="flex-1">
                        <CardTitle className="text-lg">{collection.name}</CardTitle>
                        <CardDescription>{collection.description}</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">
                        {collection.itemCount} items
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {collection.lastModified}
                      </span>
                    </div>
                    <Badge variant="outline" className="mt-2">
                      {collection.type}
                    </Badge>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            <TabsContent value="blog">
              <div className="text-center py-8 text-muted-foreground">
                Blog collections will appear here
              </div>
            </TabsContent>

            <TabsContent value="products">
              <div className="text-center py-8 text-muted-foreground">
                Product collections will appear here
              </div>
            </TabsContent>

            <TabsContent value="people">
              <div className="text-center py-8 text-muted-foreground">
                People collections will appear here
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default Collections;
