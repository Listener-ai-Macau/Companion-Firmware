#ifndef COMPANION_PENDANT_EPAPER_PET_VISUAL_STYLE_H
#define COMPANION_PENDANT_EPAPER_PET_VISUAL_STYLE_H

/*
 * Generated-art style contract:
 * genref_sheet_12_inner_faces_v5 uses the generated 12-pose inner-face sheet
 * as the art baseline.  The physical shell owns the outer cat silhouette;
 * firmware composes the generated-sheet eyes, brows, mouth, cheeks, and marks
 * as a parametric rig instead of replaying fixed sticker bitmaps.
 */
#define COMP_PET_STYLE_NAME "genref_sheet_12_inner_faces_v5"

#define COMP_PET_STYLE_CANVAS_CENTER_X 100
#define COMP_PET_STYLE_EYE_CENTER_Y 83
#define COMP_PET_STYLE_EYE_HALF_SPACING 29

#define COMP_PET_STYLE_EYE_BASE_RX 10
#define COMP_PET_STYLE_EYE_OPEN_RX_GAIN 4
#define COMP_PET_STYLE_EYE_BASE_RY 8
#define COMP_PET_STYLE_EYE_OPEN_RY_GAIN 18
#define COMP_PET_STYLE_EYE_ARC_SMILE_RY 10
#define COMP_PET_STYLE_EYE_ARC_SLEEPY_RY 8
#define COMP_PET_STYLE_HIGHLIGHT_RX 3
#define COMP_PET_STYLE_HIGHLIGHT_RY 5

#define COMP_PET_STYLE_NOSE_Y 111
#define COMP_PET_STYLE_MOUTH_CENTER_Y 123
#define COMP_PET_STYLE_MOUTH_BASE_WIDTH 16
#define COMP_PET_STYLE_MOUTH_BASE_INNER 7
#define COMP_PET_STYLE_MOUTH_BASE_HEIGHT 7

#define COMP_PET_STYLE_CHEEK_LEFT_X0 37
#define COMP_PET_STYLE_CHEEK_LEFT_X1 47
#define COMP_PET_STYLE_CHEEK_RIGHT_X0 163
#define COMP_PET_STYLE_CHEEK_RIGHT_X1 153
#define COMP_PET_STYLE_CHEEK_Y0 120
#define COMP_PET_STYLE_CHEEK_Y1 126
#define COMP_PET_STYLE_CHEEK_DOT_LEFT_X 39
#define COMP_PET_STYLE_CHEEK_DOT_RIGHT_X 161
#define COMP_PET_STYLE_CHEEK_DOT_Y 119

#endif /* COMPANION_PENDANT_EPAPER_PET_VISUAL_STYLE_H */
