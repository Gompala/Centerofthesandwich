const fs = require('fs');
const path = require('path');

module.exports = function(eleventyConfig) {
  eleventyConfig.addPassthroughCopy("admin");
  eleventyConfig.addPassthroughCopy("logo");
  eleventyConfig.addPassthroughCopy({ "shared.css": "shared.css" });
  eleventyConfig.addPassthroughCopy("images");
  eleventyConfig.addWatchTarget("./shared.css");

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
    templateFormats: ["njk", "md", "html"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk"
  };
};
