"""Readable revision evidence shared by analysis, presentation and the viewer."""
import streamlit as st
from PIL import Image
from dashboard.components import show_image


def change_overlay(revision):
    """Display-only highlights; raw measurements and exported evidence stay intact."""
    if revision.current_image is None or revision.diff_mask is None:
        return None
    image = revision.current_image.convert('RGB').copy()
    mask = revision.diff_mask.convert('L')
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.NEAREST)
    tint = Image.new('RGB', image.size, (220, 38, 38))
    return Image.composite(Image.blend(image, tint, 0.65), image, mask)


def render_revision_evidence(result):
    rv = result.revision
    if rv is None:
        st.info('Revision comparison was not run or is unavailable. Check analysis coverage.')
        return
    st.write(rv.summary)
    st.caption(f'Representative page {rv.page_index + 1} · {rv.pages_compared} signed/current page comparison(s). All-page coverage is in the analysis report.')
    if rv.error:
        st.warning(rv.error)
    if rv.signed_rev_image is not None and rv.current_image is not None:
        a, b = st.columns(2)
        with a: show_image(rv.signed_rev_image, 'Earliest signed revision')
        with b: show_image(rv.current_image, 'Current revision')
        visible = rv.diff_image is not None and rv.diff_image.getbbox() is not None
        if visible:
            st.caption(f'Changed area: {rv.changed_area_pct:.4f}% of the representative page. Red highlights are display aids, not a forgery verdict.')
            overlay = change_overlay(rv)
            if overlay is not None:
                show_image(overlay, 'Current page with changed pixels highlighted in red')
            if rv.changed_boxes:
                # Crop only for display; keep the complete raw evidence unchanged.
                x0 = min(box[0] for box in rv.changed_boxes)
                y0 = min(box[1] for box in rv.changed_boxes)
                x1 = max(box[0] + box[2] + 1 for box in rv.changed_boxes)
                y1 = max(box[1] + box[3] + 1 for box in rv.changed_boxes)
                source = overlay if overlay is not None else rv.current_image
                bounds = (max(0, x0-30), max(0, y0-30), min(source.width, x1+30), min(source.height, y1+30))
                show_image(source.crop(bounds), 'Zoomed changed region · Same page coordinates')
            with st.expander('Raw pixel difference and threshold mask'):
                show_image(rv.diff_image, 'Raw absolute pixel difference · Black means unchanged')
                show_image(rv.diff_mask, 'Threshold mask · White marks pixels above the configured threshold')
        else:
            st.info('No visible pixel difference between the signed and current page. A black raw difference image means unchanged pixels, not a broken image. Signed-byte tampering can also leave page appearance unchanged.')
    else:
        if rv.current_image is not None:
            show_image(rv.current_image, 'Current document page')
        if rv.signed_rev_index is None:
            st.info('No signed revision is available as a visual baseline. An unsigned document cannot provide a signed-versus-current image.')
        elif not rv.has_incremental_updates:
            st.info('There is no later revision to compare with this signed document. The current page is shown above.')
        else:
            st.info('A signed/current image pair is unavailable for this page. Check page additions/removals and processing limits.')
    if rv.revisions:
        st.dataframe([{'Revision':r.index+1, 'Signed':r.is_signed, 'End offset':r.end_offset, 'Pages':r.page_count} for r in rv.revisions], hide_index=True, width='stretch')
    if result.timeline:
        with st.expander('Consecutive revision timeline'):
            st.json(result.timeline)
