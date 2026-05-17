const fs = require('fs');
const path = require('path');

module.exports = function(eleventyConfig) {
  // Copy entire directories and files to output
  eleventyConfig.addPassthroughCopy("admin");
  eleventyConfig.addPassthroughCopy("logo");
  eleventyConfig.addPassthroughCopy("images");
  
  // Copy CSS using glob
  eleventyConfig.addPassthroughCopy("**/*.css");

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
