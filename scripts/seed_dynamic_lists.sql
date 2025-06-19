-- Seed script for initial dynamic lists and items
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('story_genres', 'Story Genres');
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('image_styles_app', 'Image Styles (Application)');
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('writing_styles', 'Writing Styles');
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('word_to_picture_ratio', 'Word to Picture Ratio');
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('text_density', 'Text Density');

INSERT OR
IGNORE INTO dynamic_list_items (list_name, item_value, item_label, is_active, sort_order, additional_config)
-- Added additional_config
VALUES
    -- Genres (match StoryGenre enum values exactly)
    ('story_genres', 'Children''s', 'Children’s', 1, 1, NULL),
    ('story_genres', 'Sci-Fi', 'Sci-Fi', 1, 2, NULL),
    ('story_genres', 'Drama', 'Drama', 1, 3, NULL),
    ('story_genres', 'Horror', 'Horror', 1, 4, NULL),
    ('story_genres', 'Action', 'Action', 1, 5, NULL),
    ('story_genres', 'Fantasy', 'Fantasy', 1, 6, NULL),
    ('story_genres', 'Mystery', 'Mystery', 1, 7, NULL),
    ('story_genres', 'Romance', 'Romance', 1, 8, NULL),
    ('story_genres', 'Thriller', 'Thriller', 1, 9, NULL),
    ('story_genres', 'Comedy', 'Comedy', 1, 10, NULL),
    -- Image Styles (match ImageStyle enum values exactly)
    ('image_styles_app', 'Default', 'Default', 1, 1, NULL),
    ('image_styles_app', 'Cartoon', 'Cartoon', 1, 2, NULL),
    ('image_styles_app', 'Watercolor', 'Watercolor', 1, 3, NULL),
    ('image_styles_app', 'Photorealistic', 'Photorealistic', 1, 4, NULL),
    ('image_styles_app', 'Pixel Art', 'Pixel Art', 1, 5, NULL),
    ('image_styles_app', 'Fantasy Art', 'Fantasy Art', 1, 6, NULL),
    ('image_styles_app', 'Sci-Fi Concept Art', 'Sci-Fi Concept Art', 1, 7, NULL),
    ('image_styles_app', 'Anime', 'Anime', 1, 8, NULL),
    ('image_styles_app', 'Vintage Comic Book Art', 'Vintage Comic Book Art', 1, 9, NULL),
    ('image_styles_app', 'Minimalist', 'Minimalist', 1, 10, NULL),
    ('image_styles_app', 'Noir', 'Noir', 1, 11, NULL),
    -- Word-to-Picture Ratio (match WordToPictureRatio enum values exactly)
    ('word_to_picture_ratio', 'One image per page', 'One image per page', 1, 1, NULL),
    ('word_to_picture_ratio', 'One image per two pages', 'One image per two pages', 1, 2, NULL),
    ('word_to_picture_ratio', 'One image per paragraph', 'One image per paragraph', 1, 3, NULL),
    -- Text Density (match TextDensity enum values exactly)
    ('text_density', 'Concise (~30-50 words)', 'Concise (~30-50 words)', 1, 1, NULL),
    ('text_density', 'Standard (~60-90 words)', 'Standard (~60-90 words)', 1, 2, NULL),
    ('text_density', 'Detailed (~100-150 words)', 'Detailed (~100-150 words)', 1, 3, NULL);
