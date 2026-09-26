/**
 * PostTab Component — Next-Gen Post Editor Panel with Lucide Icons
 */

import { useState } from 'react';
import { Edit3, Clock, Eye, Rocket, RotateCcw, AlertCircle, Info, Loader2, ImagePlus, X } from 'lucide-react';
import api, { startCampaign } from '../api';
import '../styles/PostTab.css';

export default function PostTab({ groups, selectedIds, onCampaignStarted }) {
  const [content, setContent] = useState('');
  const [delayMin, setDelayMin] = useState('0');
  const [delaySec, setDelaySec] = useState('10');
  const [loading, setLoading] = useState(false);
  const [uploadingImages, setUploadingImages] = useState(false);
  const [error, setError] = useState('');
  const [selectedImages, setSelectedImages] = useState([]);

  const selectedGroups = groups.filter((g) => selectedIds.includes(g.id));
  const selectedCount = selectedGroups.length;

  const handlePreview = () => {
    if (selectedCount === 0) {
      alert("Vui lòng chọn ít nhất 1 Group trong tab 'Danh sách Group'.");
      return;
    }
    if (!content.trim()) {
      alert('Vui lòng nhập nội dung bài viết.');
      return;
    }
    alert(
      `👁 Xem trước bài đăng:\n\nGroup nhận bài: ${selectedCount} nhóm\n\n--- NỘI DUNG ---\n${content}`
    );
  };

  const handleImageSelection = (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const remainingSlots = 10 - selectedImages.length;
    if (remainingSlots <= 0) {
      alert('Bạn chỉ được chọn tối đa 10 ảnh cho mỗi bài đăng.');
      event.target.value = '';
      return;
    }

    const newFiles = files.slice(0, remainingSlots).map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random()}`,
      file,
      preview: URL.createObjectURL(file),
    }));

    setSelectedImages((prev) => [...prev, ...newFiles]);
    event.target.value = '';
  };

  const removeImage = (id) => {
    setSelectedImages((prev) => prev.filter((image) => image.id !== id));
  };

  const handlePublish = async () => {
    if (selectedCount === 0) {
      alert("Vui lòng chọn ít nhất 1 Group trong tab 'Danh sách Group'.");
      return;
    }
    if (!content.trim()) {
      alert('Vui lòng nhập nội dung bài viết.');
      return;
    }

    const confirmed = window.confirm(
      `🚀 Xác nhận xuất bản bài viết tới ${selectedCount} Group đã chọn?`
    );
    if (!confirmed) return;

    setLoading(true);
    setUploadingImages(false);
    setError('');

    let uploadedImagePaths = [];
    const delay = Math.max(1, Number(delayMin || 0) * 60 + Number(delaySec || 0));

    try {
      if (selectedImages.length > 0) {
        setUploadingImages(true);
        const formData = new FormData();
        selectedImages.forEach(({ file }) => {
          formData.append('files', file);
        });

        const uploadRes = await api.post('/api/upload/images', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        uploadedImagePaths = uploadRes.data.images || [];
      }

      const res = await startCampaign({
        group_ids: selectedGroups.map((g) => g.id),
        group_names: selectedGroups.map((g) => g.name),
        content: content.trim(),
        delay_seconds: delay,
        images: uploadedImagePaths,
      });

      if (res.data.success) {
        if (onCampaignStarted) onCampaignStarted();
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
      setUploadingImages(false);
    }
  };

  const handleReset = () => {
    setContent('');
    setSelectedImages([]);
    setError('');
  };

  const handleDelayChange = (setter, value) => {
    setter(value.replace(/\D/g, '').slice(0, 2));
  };

  const normalizeDelay = (setter, value, max) => {
    const normalized = Math.min(max, Math.max(0, Number(value || 0)));
    setter(String(normalized));
  };

  return (
    <div className="main-card-panel">
      <div className="panel-header">
        <div className="panel-header-title">
          <Edit3 size={22} />
          <span>Soạn thảo nội dung & Xuất bản bài viết Marketing</span>
        </div>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-sub)', fontWeight: '600' }}>
          Group mục tiêu: <strong style={{ color: 'var(--accent-cyan)' }}>{selectedCount}</strong> / {groups.length} nhóm
        </span>
      </div>

      <div className="image-upload-section">
        <label className="upload-label">
          Hình ảnh đính kèm (1–10 ảnh)
        </label>

        <div className="upload-box">
          <input
            id="post-image-upload"
            type="file"
            accept="image/*"
            multiple
            className="hidden-file-input"
            onChange={handleImageSelection}
            disabled={selectedImages.length >= 10}
          />

          <label htmlFor="post-image-upload" className="upload-trigger">
            <ImagePlus size={18} />
            <span>Thêm ảnh</span>
          </label>

          <div className="image-count-badge">
            {selectedImages.length}/10 ảnh
          </div>
        </div>

        {selectedImages.length > 0 && (
          <div className="image-preview-grid">
            {selectedImages.map((image) => (
              <div key={image.id} className="image-preview-item">
                <img src={image.preview} alt="Preview" />
                <button type="button" className="image-remove-btn" onClick={() => removeImage(image.id)}>
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Editor Box */}
      <div>
        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-sub)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Nội dung bài viết quảng cáo
        </label>
        <textarea
          className="editor-textarea"
          placeholder="Nhập nội dung quảng cáo, thông tin khuyến mãi hoặc tin đăng bán hàng..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      </div>

      {/* Delay Settings Bar */}
      <div className="delay-settings-bar">
        <div className="delay-label-group">
          <Clock size={18} />
          <span>Khoảng cách giữa các bài đăng:</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="number"
            className="number-stepper"
            min={0}
            max={60}
            value={delayMin}
            inputMode="numeric"
            aria-label="Số phút giữa các bài đăng"
            onChange={(e) => handleDelayChange(setDelayMin, e.target.value)}
            onBlur={(e) => normalizeDelay(setDelayMin, e.target.value, 60)}
          />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-sub)' }}>phút</span>
          <input
            type="number"
            className="number-stepper"
            min={0}
            max={59}
            value={delaySec}
            inputMode="numeric"
            aria-label="Số giây giữa các bài đăng"
            onChange={(e) => handleDelayChange(setDelaySec, e.target.value)}
            onBlur={(e) => normalizeDelay(setDelaySec, e.target.value, 59)}
          />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-sub)' }}>giây</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', marginLeft: 'auto' }}>
          <Info size={14} />
          <span>Mỗi bài đăng sẽ giãn cách tự động theo đúng thời gian này</span>
        </div>
      </div>

      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-rose)', background: 'rgba(244, 63, 94, 0.1)', padding: '12px 16px', borderRadius: '10px', fontSize: '0.88rem', border: '1px solid rgba(244, 63, 94, 0.2)' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Action CTA Bar */}
      <div className="cta-button-group">
        <button className="btn-cta-secondary" onClick={handleReset}>
          <RotateCcw size={16} /> Làm mới
        </button>
        <button className="btn-cta-secondary" onClick={handlePreview}>
          <Eye size={16} /> Xem trước
        </button>
        <button className="btn-cta-primary" onClick={handlePublish} disabled={loading || uploadingImages}>
          {loading || uploadingImages ? (
            <>
              <Loader2 size={18} className="spinner-anim" /> {uploadingImages ? 'Đang upload ảnh...' : 'Đang tiến hành đăng bài...'}
            </>
          ) : (
            <>
              <Rocket size={20} /> BẮT ĐẦU ĐĂNG BÀI BÀI VIẾT
            </>
          )}
        </button>
      </div>
    </div>
  );
}
