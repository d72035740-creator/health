import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir: process.env.AEQUOR_NEXT_DIST_DIR ?? ".next-aequor",
};

export default nextConfig;
