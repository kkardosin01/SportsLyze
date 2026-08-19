/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@sportslyze/api-client", "@sportslyze/shared-types", "@sportslyze/ui"],
};

module.exports = nextConfig;
