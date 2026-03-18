import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["better-sqlite3"],
  productionBrowserSourceMaps: true, // Required for test coverage mapping
};

export default nextConfig;
