import { apiUpload } from "@/lib/api/client";

export type UploadedImage = {
  url: string;
  content_type: string;
  size: number;
};

export const uploadsApi = {
  /** Upload an image and receive its site-relative URL (e.g. `/media/...`). */
  uploadImage(file: File): Promise<UploadedImage> {
    const formData = new FormData();
    formData.append("file", file);
    return apiUpload<UploadedImage>("/uploads/images", formData);
  },
};
