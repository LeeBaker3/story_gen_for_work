-- Seed script for initial dynamic lists and items
-- NOTE: Renamed 'story_genres' -> 'genres' and 'image_styles_app' -> 'image_styles' to match
-- application code (crud.is_dynamic_list_item_in_use and tests) which reference
-- list_name values 'genres' and 'image_styles'. If you already have rows with the
-- old names, you may want to migrate or delete them manually before re-seeding.
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('genres', 'Story Genres');
INSERT OR
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('image_styles', 'Image Styles');
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
IGNORE INTO dynamic_lists (list_name, list_label)
VALUES
    ('genders', 'Genders');

INSERT OR
IGNORE INTO dynamic_list_items (list_name, item_value, item_label, is_active, sort_order, additional_config)
-- Added additional_config
VALUES
    -- Genres (match StoryGenre enum values exactly)
    ('genres', 'Children''s', 'Children’s', 1, 1, NULL),
    ('genres', 'Sci-Fi', 'Sci-Fi', 1, 2, NULL),
    ('genres', 'Drama', 'Drama', 1, 3, NULL),
    ('genres', 'Horror', 'Horror', 1, 4, NULL),
    ('genres', 'Action', 'Action', 1, 5, NULL),
    ('genres', 'Fantasy', 'Fantasy', 1, 6, NULL),
    ('genres', 'Mystery', 'Mystery', 1, 7, NULL),
    ('genres', 'Romance', 'Romance', 1, 8, NULL),
    ('genres', 'Thriller', 'Thriller', 1, 9, NULL),
    ('genres', 'Comedy', 'Comedy', 1, 10, NULL),
    -- Image Styles (match ImageStyle enum values exactly)
    ('image_styles', 'Default', 'Default', 1, 1, NULL),
    ('image_styles', 'Cartoon', 'Cartoon', 1, 2, NULL),
    ('image_styles', 'Watercolor', 'Watercolor', 1, 3, NULL),
    ('image_styles', 'Photorealistic', 'Photorealistic', 1, 4, NULL),
    ('image_styles', 'Pixel Art', 'Pixel Art', 1, 5, NULL),
    ('image_styles', 'Fantasy Art', 'Fantasy Art', 1, 6, NULL),
    ('image_styles', 'Sci-Fi Concept Art', 'Sci-Fi Concept Art', 1, 7, NULL),
    ('image_styles', 'Anime', 'Anime', 1, 8, NULL),
    ('image_styles', 'Vintage Comic Book Art', 'Vintage Comic Book Art', 1, 9, NULL),
    ('image_styles', 'Minimalist', 'Minimalist', 1, 10, NULL),
    ('image_styles', 'Noir', 'Noir', 1, 11, NULL),
    -- Word-to-Picture Ratio (match WordToPictureRatio enum values exactly)
    ('word_to_picture_ratio', 'One image per page', 'One image per page', 1, 1, NULL),
    ('word_to_picture_ratio', 'One image per two pages', 'One image per two pages', 1, 2, NULL),
    ('word_to_picture_ratio', 'One image per paragraph', 'One image per paragraph', 1, 3, NULL),
    -- Text Density (match TextDensity enum values exactly)
    ('text_density', 'Concise (~30-50 words)', 'Concise (~30-50 words)', 1, 1, NULL),
    ('text_density', 'Standard (~60-90 words)', 'Standard (~60-90 words)', 1, 2, NULL),
    ('text_density', 'Detailed (~100-150 words)', 'Detailed (~100-150 words)', 1, 3, NULL),
    -- Genders (generic list; free-form allowed but common options provided)
    ('genders', 'Female', 'Female', 1, 1, NULL),
    ('genders', 'Male', 'Male', 1, 2, NULL),
    ('genders', 'Non-binary', 'Non-binary', 1, 3, NULL),
    ('genders', 'Other', 'Other', 1, 4, NULL),
    ('genders', 'Prefer not to say', 'Prefer not to say', 1, 5, NULL);
