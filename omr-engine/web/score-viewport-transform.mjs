/**
 * Transforma rectángulos de coordenadas de análisis al espacio CSS del visor.
 * Las dimensiones y offsets deben proceder del renderizador/host; no se adivinan.
 */
export class ScoreViewportTransform {
  constructor({
    source_width, source_height, rendered_width, rendered_height,
    offset_left = 0, offset_top = 0, scroll_left = 0, scroll_top = 0,
    page_index,
  } = {}) {
    const positive = ["source_width", "source_height", "rendered_width", "rendered_height"];
    const values = { source_width, source_height, rendered_width, rendered_height };
    for (const key of positive) {
      if (!Number.isFinite(values[key]) || values[key] <= 0) {
        throw new RangeError(key + " debe ser positivo");
      }
    }
    for (const [key, value] of Object.entries({ offset_left, offset_top, scroll_left, scroll_top })) {
      if (!Number.isFinite(value)) throw new TypeError(key + " debe ser finito");
    }
    if (!Number.isInteger(page_index) || page_index < 0) {
      throw new RangeError("page_index debe ser entero no negativo");
    }
    this.scale_x = rendered_width / source_width;
    this.scale_y = rendered_height / source_height;
    this.offset_left = offset_left;
    this.offset_top = offset_top;
    this.scroll_left = scroll_left;
    this.scroll_top = scroll_top;
    this.page_index = page_index;
  }

  mapRect(rect) {
    if (!rect || !Number.isFinite(rect.x) || !Number.isFinite(rect.y) ||
        !Number.isFinite(rect.width) || !Number.isFinite(rect.height) ||
        rect.width <= 0 || rect.height <= 0) {
      throw new TypeError("El rectángulo requiere x/y y dimensiones positivas");
    }
    return {
      left: this.offset_left + rect.x * this.scale_x - this.scroll_left,
      top: this.offset_top + rect.y * this.scale_y - this.scroll_top,
      width: rect.width * this.scale_x,
      height: rect.height * this.scale_y,
    };
  }

  mapVisualState(visualState) {
    if (!visualState || !Array.isArray(visualState.highlights)) {
      throw new TypeError("Se requiere un estado visual del cursor");
    }
    const visible = visualState.page_index === this.page_index && !visualState.ambiguous_location;
    return {
      page_index: this.page_index,
      visible,
      ambiguous_location: Boolean(visualState.ambiguous_location),
      highlights: visible ? visualState.highlights
        .filter(item => item.page_index === this.page_index)
        .map(item => ({ ...item, rect: this.mapRect(item) })) : [],
    };
  }
}
