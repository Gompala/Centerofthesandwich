const fs = require('fs');
const path = require('path');

module.exports = function(eleventyConfig) {
  // Copy static files directly to output
  eleventyConfig.addPassthroughCopy("admin");
  eleventyConfig.addPassthroughCopy("logo");
  eleventyConfig.addPassthroughCopy("shared.css");
  eleventyConfig.addPassthroughCopy("images");

  // Watch CSS files for changes
  eleventyConfig.addWatchTarget("./shared.css");

  // Add news data from _data/news.json
  eleventyConfig.addGlobalData("news", () => {
    const newsFile = path.join(__dirname, "_data", "news.json");
    if (fs.existsSync(newsFile)) {
      return JSON.parse(fs.readFileSync(newsFile, "utf8"));
    }
    return { categories: {} };
  });

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
      data: "_data"
    },
    templateFormats: ["html", "md", "njk"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk"
  };
};
