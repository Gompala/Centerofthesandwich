module.exports = function(eleventyConfig) {
  // Copy static files directly to output
  eleventyConfig.addPassthroughCopy("admin");
  eleventyConfig.addPassthroughCopy("logo");
  eleventyConfig.addPassthroughCopy("shared.css");
  eleventyConfig.addPassthroughCopy("images");

  // Watch CSS files for changes
  eleventyConfig.addWatchTarget("./shared.css");

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